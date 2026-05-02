"""
Oxford-IIIT Pet 分割训练（U-Net, segmentation_models_pytorch）
标签来源：data/pets/annotations/trimaps/*.png
导出：backend/weights/seg_unet.pth

运行示例：
python training/train_seg_unet.py --images_dir data/pets/images --trimaps_dir data/pets/annotations/trimaps --epochs 10 --bs 8 --img_size 256
随机初始化对比：
python training/train_seg_unet.py --images_dir data/pets/images --trimaps_dir data/pets/annotations/trimaps --epochs 30 --bs 8 --img_size 256 --encoder_weights none --out backend/weights/seg_unet_random_init.pth --curves_out backend/artifacts/segmentation/seg_curves_random_init.json
"""

from pathlib import Path
import argparse
import json
from typing import List, Tuple

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
import segmentation_models_pytorch as smp
from tqdm import tqdm
from split_utils import split_segmentation_ids


class PetSegDataset(Dataset):
    def __init__(self, images_dir: Path, trimaps_dir: Path, image_ids: List[str], img_size: int = 256):
        self.images_dir = images_dir
        self.trimaps_dir = trimaps_dir
        self.image_ids = image_ids
        self.img_tf = T.Compose([
            T.Resize((img_size, img_size)),
            T.ToTensor(),
        ])
        self.mask_tf = T.Resize((img_size, img_size), interpolation=T.InterpolationMode.NEAREST)

    def __len__(self):
        return len(self.image_ids)

    def __getitem__(self, idx):
        image_id = self.image_ids[idx]
        img_path = self.images_dir / f"{image_id}.jpg"
        mask_path = self.trimaps_dir / f"{image_id}.png"

        image = Image.open(img_path).convert("RGB")
        trimap = Image.open(mask_path)

        image = self.img_tf(image)
        trimap = self.mask_tf(trimap)
        trimap = np.array(trimap, dtype=np.uint8)

        # Oxford trimap: 1=前景, 2=背景, 3=边界
        # 二值分割：前景=1，其余=0
        mask = (trimap == 1).astype(np.float32)
        mask = torch.from_numpy(mask).unsqueeze(0)

        return image, mask


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images_dir", type=str, default="data/pets/images")
    parser.add_argument("--trimaps_dir", type=str, default="data/pets/annotations/trimaps")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--bs", type=int, default=8)
    parser.add_argument("--img_size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--out", type=str, default="backend/weights/seg_unet.pth")
    parser.add_argument("--curves_out", type=str, default=None)
    parser.add_argument(
        "--encoder_weights",
        type=str,
        default="imagenet",
        choices=["imagenet", "none"],
        help="U-Net 编码器初始化方式；none 用于随机初始化对比实验",
    )
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--pin_memory", action="store_true", default=True)
    return parser.parse_args()


def dice_score(pred: torch.Tensor, target: torch.Tensor, eps: float = 1e-6) -> float:
    pred = (pred > 0.5).float()
    inter = (pred * target).sum(dim=(1, 2, 3))
    union = pred.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3))
    dice = (2 * inter + eps) / (union + eps)
    return dice.mean().item()


def main():
    args = parse_args()
    if args.encoder_weights == "none" and args.out == "backend/weights/seg_unet.pth":
        args.out = "backend/weights/seg_unet_random_init.pth"

    images_dir = Path(args.images_dir)
    trimaps_dir = Path(args.trimaps_dir)

    if not images_dir.exists() or not trimaps_dir.exists():
        raise FileNotFoundError(f"分割数据路径不存在: {images_dir} / {trimaps_dir}")

    train_ids, val_ids, _ = split_segmentation_ids(images_dir)
    train_ds = PetSegDataset(images_dir, trimaps_dir, train_ids, img_size=args.img_size)
    val_ds = PetSegDataset(images_dir, trimaps_dir, val_ids, img_size=args.img_size)

    use_pin_memory = bool(args.pin_memory and torch.cuda.is_available())
    train_loader = DataLoader(
        train_ds,
        batch_size=args.bs,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=use_pin_memory,
        persistent_workers=args.num_workers > 0,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.bs,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=use_pin_memory,
        persistent_workers=args.num_workers > 0,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        torch.backends.cudnn.benchmark = True
    encoder_weights = None if args.encoder_weights == "none" else args.encoder_weights
    print(f"Segmentation model: U-Net(resnet34 encoder), encoder_weights={encoder_weights}")
    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights=encoder_weights,
        in_channels=3,
        classes=1,
    ).to(device)

    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_dice = 0.0
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("DataLoader ready, start training...")

    curves = {"epochs": [], "train_loss": [], "val_loss": [], "val_dice": []}

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0

        train_pbar = tqdm(train_loader, desc=f"Epoch [{epoch}/{args.epochs}] Train", leave=False)
        for images, masks in train_pbar:
            images, masks = images.to(device), masks.to(device)
            logits = model(images)
            loss = criterion(logits, masks)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * images.size(0)
            train_pbar.set_postfix(loss=f"{loss.item():.4f}")

        train_loss /= len(train_loader.dataset)

        model.eval()
        val_loss = 0.0
        val_dice = 0.0
        val_pbar = tqdm(val_loader, desc=f"Epoch [{epoch}/{args.epochs}] Val", leave=False)
        with torch.no_grad():
            for images, masks in val_pbar:
                images, masks = images.to(device), masks.to(device)
                logits = model(images)
                loss = criterion(logits, masks)
                probs = torch.sigmoid(logits)

                val_loss += loss.item() * images.size(0)
                val_dice += dice_score(probs, masks) * images.size(0)
                val_pbar.set_postfix(loss=f"{loss.item():.4f}")

        val_loss /= len(val_loader.dataset)
        val_dice /= len(val_loader.dataset)

        print(f"Epoch [{epoch}/{args.epochs}] train_loss={train_loss:.4f} val_loss={val_loss:.4f} val_dice={val_dice:.4f}")

        curves["epochs"].append(epoch)
        curves["train_loss"].append(round(train_loss, 4))
        curves["val_loss"].append(round(val_loss, 4))
        curves["val_dice"].append(round(val_dice, 4))

        if val_dice > best_dice:
            best_dice = val_dice
            torch.save(model.state_dict(), out_path)
            print(f"保存最佳分割模型: {out_path} (dice={best_dice:.4f})")

    if args.curves_out:
        curves_path = Path(args.curves_out)
    else:
        curves_name = "seg_curves.json" if args.encoder_weights == "imagenet" else "seg_curves_random_init.json"
        curves_path = Path("backend/artifacts/segmentation") / curves_name
    curves_path.parent.mkdir(parents=True, exist_ok=True)
    with open(curves_path, "w", encoding="utf-8") as f:
        json.dump(curves, f, ensure_ascii=False)
    print(f"分割训练曲线已保存: {curves_path}")


if __name__ == "__main__":
    main()

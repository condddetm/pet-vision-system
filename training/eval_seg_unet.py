"""
Oxford-IIIT Pet 分割评估脚本（U-Net, segmentation_models_pytorch）
输出到 backend/artifacts/segmentation:
- seg_metrics.json  (mIoU, Dice, PixelAcc)

运行示例：
python training/eval_seg_unet.py --images_dir data/pets/images --trimaps_dir data/pets/annotations/trimaps --ckpt backend/weights/seg_unet.pth --out_dir backend/artifacts/segmentation
"""

from pathlib import Path
import argparse
import json
from typing import List, Tuple

import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
import segmentation_models_pytorch as smp
from tqdm import tqdm
from split_utils import split_segmentation_ids


class PetSegEvalDataset(Dataset):
    def __init__(self, images_dir: Path, trimaps_dir: Path, image_ids: List[str], img_size: int = 256):
        self.images_dir = images_dir
        self.trimaps_dir = trimaps_dir
        self.image_ids = image_ids
        self.img_tf = T.Compose([T.Resize((img_size, img_size)), T.ToTensor()])
        self.mask_tf = T.Resize((img_size, img_size), interpolation=T.InterpolationMode.NEAREST)

    def __len__(self):
        return len(self.image_ids)

    def __getitem__(self, idx):
        image_id = self.image_ids[idx]
        image = Image.open(self.images_dir / f"{image_id}.jpg").convert("RGB")
        trimap = Image.open(self.trimaps_dir / f"{image_id}.png")
        image = self.img_tf(image)
        trimap = self.mask_tf(trimap)
        trimap = np.array(trimap, dtype=np.uint8)
        mask = (trimap == 1).astype(np.float32)
        return image, torch.from_numpy(mask).unsqueeze(0)


def dice_score(pred: np.ndarray, target: np.ndarray, eps: float = 1e-6) -> float:
    inter = (pred * target).sum()
    return (2 * inter + eps) / (pred.sum() + target.sum() + eps)


def iou_score(pred: np.ndarray, target: np.ndarray, eps: float = 1e-6) -> float:
    inter = (pred * target).sum()
    union = pred.sum() + target.sum() - inter
    return (inter + eps) / (union + eps)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--images_dir", default="data/pets/images")
    p.add_argument("--trimaps_dir", default="data/pets/annotations/trimaps")
    p.add_argument("--ckpt", default="backend/weights/seg_unet.pth")
    p.add_argument("--out_dir", default="backend/artifacts/segmentation")
    p.add_argument("--img_size", type=int, default=256)
    p.add_argument("--bs", type=int, default=8)
    return p.parse_args()


def main():
    args = parse_args()
    images_dir = Path(args.images_dir)
    trimaps_dir = Path(args.trimaps_dir)
    ckpt_path = Path(args.ckpt)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not images_dir.exists():
        raise FileNotFoundError(f"images_dir 不存在: {images_dir}")
    if not ckpt_path.exists():
        raise FileNotFoundError(f"权重不存在: {ckpt_path}")

    _, _, test_ids = split_segmentation_ids(images_dir)
    test_ids = [image_id for image_id in test_ids if (trimaps_dir / f"{image_id}.png").exists()]

    ds = PetSegEvalDataset(images_dir, trimaps_dir, test_ids, img_size=args.img_size)
    loader = DataLoader(ds, batch_size=args.bs, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = smp.Unet(encoder_name="resnet34", encoder_weights=None, in_channels=3, classes=1).to(device)
    model.load_state_dict(torch.load(ckpt_path, map_location=device))
    model.eval()

    all_dice, all_iou, all_pix = [], [], []

    with torch.no_grad():
        for images, masks in tqdm(loader, desc="Evaluating"):
            images = images.to(device)
            logits = model(images)
            probs = torch.sigmoid(logits).cpu().numpy()
            masks_np = masks.numpy()

            for i in range(len(probs)):
                pred = (probs[i, 0] > 0.5).astype(np.float32)
                tgt = masks_np[i, 0].astype(np.float32)
                all_dice.append(dice_score(pred, tgt))
                all_iou.append(iou_score(pred, tgt))
                all_pix.append((pred == tgt).mean())

    metrics = {
        "miou": round(float(np.mean(all_iou)), 4),
        "dice": round(float(np.mean(all_dice)), 4),
        "pixel_acc": round(float(np.mean(all_pix)), 4),
        "num_eval_samples": len(all_dice),
        "num_val_samples": len(all_dice),
        "evaluation_split": "test",
    }

    # 主实验保留历史镜像；对比实验写到 random_init 等独立目录时不覆盖主指标。
    mirror_dirs = [out_dir]
    if out_dir == Path("backend/artifacts/segmentation"):
        mirror_dirs.append(Path("backend/artifacts/classification"))

    for dest in mirror_dirs:
        dest.mkdir(parents=True, exist_ok=True)
        with open(dest / "seg_metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

    print("分割评估完成:", metrics)


if __name__ == "__main__":
    main()

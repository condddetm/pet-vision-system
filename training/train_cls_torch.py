"""
Oxford-IIIT Pet 分类训练（纯 PyTorch）
导出：backend/weights/cls_torch.pth

运行示例：
python training/train_cls_torch.py --images_dir data/pets/images --epochs 50 --bs 32 --img_size 224 --patience 5
随机初始化对比：
python training/train_cls_torch.py --images_dir data/pets/images --epochs 100 --bs 32 --img_size 224 --patience 1000 --no-pretrained --out backend/weights/cls_torch_random_init.pth --curves_out backend/artifacts/classification/curves_random_init.json
"""

from pathlib import Path
import argparse
import re
import json

from PIL import Image
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
from torchvision.models import resnet34, ResNet34_Weights
from tqdm import tqdm
from split_utils import split_classification_files

PATTERN = re.compile(r"^(.*)_\d+\.jpg$")


class PetClsDataset(Dataset):
    def __init__(self, files, class_to_idx, img_size=224, train=True):
        self.files = files
        self.class_to_idx = class_to_idx
        mean = [0.485, 0.456, 0.406]
        std = [0.229, 0.224, 0.225]
        if train:
            self.tf = T.Compose([
                T.Resize((img_size, img_size)),
                T.RandomHorizontalFlip(),
                T.ColorJitter(0.1, 0.1, 0.1, 0.05),
                T.ToTensor(),
                T.Normalize(mean=mean, std=std),
            ])
        else:
            self.tf = T.Compose([
                T.Resize((img_size, img_size)),
                T.ToTensor(),
                T.Normalize(mean=mean, std=std),
            ])

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        p = self.files[idx]
        m = PATTERN.match(p.name)
        cls = m.group(1)
        y = self.class_to_idx[cls]
        x = Image.open(p).convert("RGB")
        x = self.tf(x)
        return x, y


def evaluate(model, loader, device, epoch_idx, total_epochs):
    model.eval()
    criterion = nn.CrossEntropyLoss()
    total_loss, total, correct = 0.0, 0, 0

    pbar = tqdm(loader, desc=f"Epoch [{epoch_idx}/{total_epochs}] Val", leave=False)
    with torch.no_grad():
        for x, y in pbar:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = criterion(logits, y)
            total_loss += loss.item() * x.size(0)
            pred = logits.argmax(dim=1)
            correct += (pred == y).sum().item()
            total += x.size(0)
            pbar.set_postfix(loss=f"{loss.item():.4f}")

    return total_loss / total, correct / total


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--images_dir", type=str, default="data/pets/images")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--bs", type=int, default=32)
    p.add_argument("--img_size", type=int, default=224)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--out", type=str, default="backend/weights/cls_torch.pth")
    p.add_argument("--curves_out", type=str, default=None)
    p.add_argument(
        "--pretrained",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否使用 ImageNet 预训练权重；使用 --no-pretrained 可复现随机初始化对比实验",
    )

    # Early Stopping
    p.add_argument("--patience", type=int, default=5)
    p.add_argument("--min_delta", type=float, default=1e-3)

    # LR Scheduler (ReduceLROnPlateau)
    p.add_argument("--lr_patience", type=int, default=2)
    p.add_argument("--lr_factor", type=float, default=0.5)
    p.add_argument("--min_lr", type=float, default=1e-6)

    return p.parse_args()


def main():
    args = parse_args()
    if not args.pretrained and args.out == "backend/weights/cls_torch.pth":
        args.out = "backend/weights/cls_torch_random_init.pth"

    images_dir = Path(args.images_dir)
    if not images_dir.exists():
        raise FileNotFoundError(f"分类数据路径不存在: {images_dir}")

    train_files, val_files, _, classes = split_classification_files(images_dir)
    class_to_idx = {c: i for i, c in enumerate(classes)}

    train_ds = PetClsDataset(train_files, class_to_idx, img_size=args.img_size, train=True)
    val_ds = PetClsDataset(val_files, class_to_idx, img_size=args.img_size, train=False)
    train_loader = DataLoader(train_ds, batch_size=args.bs, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.bs, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    weights = ResNet34_Weights.IMAGENET1K_V1 if args.pretrained else None
    print(f"Using device: {device}")
    print(f"Classification backbone: ResNet-34, pretrained={args.pretrained}")
    model = resnet34(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, len(classes))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=args.lr_factor,
        patience=args.lr_patience,
        min_lr=args.min_lr,
    )

    best_acc = 0.0
    best_epoch = 0
    no_improve_count = 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    curves = {"epochs": [], "train_loss": [], "val_loss": [], "val_acc": []}

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss, total = 0.0, 0

        train_pbar = tqdm(train_loader, desc=f"Epoch [{epoch}/{args.epochs}] Train", leave=False)
        for x, y in train_pbar:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = criterion(logits, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * x.size(0)
            total += x.size(0)
            train_pbar.set_postfix(loss=f"{loss.item():.4f}")

        train_loss = total_loss / total
        val_loss, val_acc = evaluate(model, val_loader, device, epoch, args.epochs)

        current_lr = optimizer.param_groups[0]["lr"]
        print(
            f"Epoch [{epoch}/{args.epochs}] "
            f"lr={current_lr:.6f} train_loss={train_loss:.4f} val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )

        curves["epochs"].append(epoch)
        curves["train_loss"].append(round(train_loss, 4))
        curves["val_loss"].append(round(val_loss, 4))
        curves["val_acc"].append(round(val_acc, 4))

        scheduler.step(val_acc)

        if val_acc > best_acc + args.min_delta:
            best_acc = val_acc
            best_epoch = epoch
            no_improve_count = 0
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "classes": classes,
                    "img_size": args.img_size,
                    "arch": "resnet34",
                    "pretrained": args.pretrained,
                    "best_acc": best_acc,
                    "best_epoch": best_epoch,
                    "train_samples": len(train_files),
                    "val_samples": len(val_files),
                    "hyperparams": {
                        "epochs": args.epochs,
                        "batch_size": args.bs,
                        "img_size": args.img_size,
                        "lr": args.lr,
                        "optimizer": "Adam",
                        "loss": "CrossEntropyLoss",
                    },
                },
                out_path,
            )
            print(f"保存最佳分类模型: {out_path} (acc={best_acc:.4f}, epoch={best_epoch})")
        else:
            no_improve_count += 1
            print(f"验证集未提升计数: {no_improve_count}/{args.patience}")

        if no_improve_count >= args.patience:
            print(
                f"Early Stopping 触发：连续 {args.patience} 轮无提升。"
                f" best_acc={best_acc:.4f}, best_epoch={best_epoch}"
            )
            break

    print(f"训练结束。最佳验证精度: {best_acc:.4f}（epoch={best_epoch}）")

    if args.curves_out:
        curves_path = Path(args.curves_out)
    else:
        curves_name = "curves.json" if args.pretrained else "curves_random_init.json"
        curves_path = Path("backend/artifacts/classification") / curves_name
    curves_path.parent.mkdir(parents=True, exist_ok=True)
    with open(curves_path, "w", encoding="utf-8") as f:
        json.dump(curves, f, ensure_ascii=False)
    print(f"训练曲线已保存: {curves_path}")


if __name__ == "__main__":
    main()

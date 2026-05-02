"""
SimpleCNN 分类评估脚本
输出到 backend/artifacts/classification/simple_cnn/:
- metrics.json
- confusion_matrix.png
- correct_*.jpg / error_*.jpg

运行示例：
python training/eval_cls_simple_cnn.py --images_dir data/pets/images --ckpt backend/weights/cls_simple_cnn.pth --out_dir backend/artifacts/classification/simple_cnn --img_size 224
"""

from pathlib import Path
import argparse
import re
import random
import json
import sys

import numpy as np
from PIL import Image, ImageDraw
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from split_utils import split_classification_files
from models.simple_cnn import SimpleCNN

PATTERN = re.compile(r"^(.*)_\d+\.jpg$")


class PetClsEvalDataset(Dataset):
    def __init__(self, files, class_to_idx, img_size=224):
        self.files = files
        self.class_to_idx = class_to_idx
        self.tf = T.Compose([
            T.Resize((img_size, img_size)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        p = self.files[idx]
        m = PATTERN.match(p.name)
        cls = m.group(1)
        y = self.class_to_idx[cls]
        img = Image.open(p).convert("RGB")
        x = self.tf(img)
        return x, y, str(p), cls


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--images_dir", type=str, default="data/pets/images")
    p.add_argument("--ckpt", type=str, default="backend/weights/cls_simple_cnn.pth")
    p.add_argument("--out_dir", type=str, default="backend/artifacts/classification/simple_cnn")
    p.add_argument("--img_size", type=int, default=224)
    p.add_argument("--bs", type=int, default=32)
    return p.parse_args()


def save_confusion_matrix(cm: np.ndarray, out_path: Path):
    plt.figure(figsize=(10, 8))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title("Confusion Matrix (SimpleCNN)")
    plt.colorbar()
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def save_case_image(img_path: Path, true_label: str, pred_label: str, score: float, out_path: Path):
    img = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    text = f"T:{true_label} | P:{pred_label} | conf:{score:.3f}"
    draw.rectangle([0, 0, img.width, 28], fill=(0, 0, 0))
    draw.text((8, 6), text, fill=(255, 255, 255))
    img.save(out_path)


def main():
    args = parse_args()
    images_dir = Path(args.images_dir)
    ckpt_path = Path(args.ckpt)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not images_dir.exists():
        raise FileNotFoundError(f"images_dir 不存在: {images_dir}")
    if not ckpt_path.exists():
        raise FileNotFoundError(f"模型权重不存在: {ckpt_path}")

    _, _, test_files, classes = split_classification_files(images_dir)
    class_to_idx = {c: i for i, c in enumerate(classes)}
    idx_to_class = {i: c for c, i in class_to_idx.items()}

    ds = PetClsEvalDataset(test_files, class_to_idx, img_size=args.img_size)
    loader = DataLoader(ds, batch_size=args.bs, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model = SimpleCNN(num_classes=len(classes))
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(device)
    model.eval()

    y_true, y_pred = [], []
    samples = []

    with torch.no_grad():
        for x, y, paths, _ in loader:
            x = x.to(device)
            logits = model(x)
            probs = torch.softmax(logits, dim=1)
            confs, preds = probs.max(dim=1)

            preds_np = preds.detach().cpu().numpy().tolist()
            confs_np = confs.detach().cpu().numpy().tolist()
            ys_np = y.numpy().tolist()

            y_true.extend(ys_np)
            y_pred.extend(preds_np)

            for i in range(len(paths)):
                t_idx = ys_np[i]
                p_idx = preds_np[i]
                t_name = idx_to_class[t_idx]
                p_name = idx_to_class[p_idx]
                conf = float(confs_np[i])
                correct = (t_idx == p_idx)
                samples.append((Path(paths[i]), t_name, p_name, conf, correct))

    acc = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    cm = confusion_matrix(y_true, y_pred)

    metrics = {
        "accuracy": round(float(acc), 4),
        "precision_macro": round(float(precision), 4),
        "recall_macro": round(float(recall), 4),
        "f1_macro": round(float(f1), 4),
        "num_eval_samples": len(y_true),
        "evaluation_split": "test",
        "model": "SimpleCNN",
    }

    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    save_confusion_matrix(cm, out_dir / "confusion_matrix.png")

    cm_json = {
        "labels": [idx_to_class[i] for i in range(len(classes))],
        "matrix": cm.tolist(),
    }
    with open(out_dir / "confusion_matrix.json", "w", encoding="utf-8") as f:
        json.dump(cm_json, f, ensure_ascii=False)

    correct_samples = [s for s in samples if s[4]]
    error_samples = [s for s in samples if not s[4]]
    random.seed(42)
    random.shuffle(correct_samples)
    random.shuffle(error_samples)

    for i, s in enumerate(correct_samples[:5], start=1):
        img_path, t_name, p_name, conf, _ = s
        save_case_image(img_path, t_name, p_name, conf, out_dir / f"correct_{i}.jpg")

    for i, s in enumerate(error_samples[:5], start=1):
        img_path, t_name, p_name, conf, _ = s
        save_case_image(img_path, t_name, p_name, conf, out_dir / f"error_{i}.jpg")

    print("SimpleCNN 评估完成，输出目录:", out_dir)
    print(metrics)


if __name__ == "__main__":
    main()

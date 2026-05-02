"""
Oxford-IIIT Pet 分类训练（fastai）
导出：backend/weights/cls_fastai.pkl

运行示例：
python training/train_cls_fastai.py --data_dir data/pets/images --epochs 8 --bs 32 --img_size 224
"""

from pathlib import Path
import argparse
from fastai.vision.all import (
    ImageDataLoaders,
    get_image_files,
    aug_transforms,
    Resize,
    vision_learner,
    accuracy,
    Precision,
    Recall,
    F1Score,
    resnet34,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="data/pets/images")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--bs", type=int, default=32)
    parser.add_argument("--img_size", type=int, default=224)
    parser.add_argument("--lr", type=float, default=3e-3)
    parser.add_argument("--out", type=str, default="backend/weights/cls_fastai.pkl")
    return parser.parse_args()


def main():
    args = parse_args()
    path = Path(args.data_dir)
    if not path.exists():
        raise FileNotFoundError(f"分类数据路径不存在: {path}")

    dls = ImageDataLoaders.from_name_re(
        path,
        get_image_files(path),
        pat=r"^(.*)_\d+\.jpg$",
        item_tfms=Resize(args.img_size),
        batch_tfms=aug_transforms(size=args.img_size),
        bs=args.bs,
        valid_pct=0.2,
        seed=42,
    )

    learn = vision_learner(
        dls,
        resnet34,
        pretrained=True,
        metrics=[accuracy, Precision(average="macro"), Recall(average="macro"), F1Score(average="macro")],
    )

    learn.fine_tune(args.epochs, base_lr=args.lr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    learn.export(out_path)
    print(f"分类模型导出完成: {out_path}")


if __name__ == "__main__":
    main()

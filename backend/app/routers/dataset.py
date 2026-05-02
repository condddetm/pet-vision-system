from pathlib import Path
import random, hashlib
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from fastapi import APIRouter
from app.core.config import BASE_DIR, ARTIFACTS_DIR

router = APIRouter(prefix="/api/dataset", tags=["dataset"])

_DATA   = BASE_DIR.parent / "data" / "pets"
_IMGS   = _DATA / "images"
_MAPS   = _DATA / "annotations" / "trimaps"
_LIST   = _DATA / "annotations" / "list.txt"
_OUT    = ARTIFACTS_DIR / "dataset_samples"

SAMPLE_BREEDS = [
    ("Abyssinian",        "猫科"),
    ("Bengal",            "猫科"),
    ("Sphynx",            "猫科"),
    ("samoyed",           "犬科"),
    ("pug",               "犬科"),
    ("beagle",            "犬科"),
]


def _load_class_distribution():
    counts = {}
    for image_path in sorted(_IMGS.glob("*.jpg")):
        breed = image_path.stem.rsplit("_", 1)[0]
        counts[breed] = counts.get(breed, 0) + 1

    return [{"name": name, "count": count} for name, count in counts.items()]


def _find_pair(breed: str):
    """Return (img_path, trimap_path) for the first matching image that has a trimap."""
    for p in sorted(_IMGS.glob(f"{breed}_*.jpg")):
        t = _MAPS / (p.stem + ".png")
        if t.exists():
            return p, t
    return None, None


def _make_overlay(orig: np.ndarray, tm: np.ndarray) -> np.ndarray:
    # Oxford trimaps: 1=foreground, 2=background, 3=boundary
    # Some files store 85/170/255; normalise to 1/2/3
    if tm.max() > 3:
        tm = np.round(tm / 85.0).astype(np.uint8)
        tm = np.clip(tm, 1, 3)

    mask_color = np.zeros((*tm.shape, 3), dtype=np.uint8)
    mask_color[tm == 1] = [72, 199, 142]   # green  – foreground
    mask_color[tm == 2] = [30,  30,  40]   # dark   – background
    mask_color[tm == 3] = [255, 200,  50]  # yellow – boundary

    overlay = (orig.astype(np.float32) * 0.55 +
               mask_color.astype(np.float32) * 0.45)
    return np.clip(overlay, 0, 255).astype(np.uint8)


@router.get("/stats")
def dataset_stats():
    class_distribution = _load_class_distribution()
    total_samples = sum(item["count"] for item in class_distribution)
    train_count = int(total_samples * 0.7)
    val_count = int(total_samples * 0.2)
    test_count = total_samples - train_count - val_count

    return {
        "name": "Oxford-IIIT Pet",
        "num_classes": len(class_distribution),
        "total_samples": total_samples,
        "split": {"train": 0.7, "val": 0.2, "test": 0.1},
        "split_counts": {"train": train_count, "val": val_count, "test": test_count},
        "augmentation": {
            "train": ["RandomHorizontalFlip", "ColorJitter(0.1,0.1,0.1,0.05)", "Resize(224)"],
            "val":   ["Resize(224)"],
        },
        "normalize": {
            "mean": [0.485, 0.456, 0.406],
            "std":  [0.229, 0.224, 0.225],
        },
        "class_distribution": class_distribution,
    }


@router.get("/samples")
def dataset_samples():
    _OUT.mkdir(parents=True, exist_ok=True)
    result = []

    for breed, species in SAMPLE_BREEDS:
        img_path, trimap_path = _find_pair(breed)
        if img_path is None:
            continue

        stem        = f"sample_{breed}"
        out_orig    = _OUT / f"{stem}_orig.jpg"
        out_mask    = _OUT / f"{stem}_mask.png"
        out_overlay = _OUT / f"{stem}_overlay.jpg"

        if not out_overlay.exists():
            orig    = Image.open(img_path).convert("RGB").resize((256, 256))
            trimap  = Image.open(trimap_path).convert("L").resize((256, 256), Image.NEAREST)
            orig_arr  = np.array(orig)
            tm_arr    = np.array(trimap)

            if tm_arr.max() > 3:
                tm_norm = np.round(tm_arr / 85.0).astype(np.uint8)
                tm_norm = np.clip(tm_norm, 1, 3)
            else:
                tm_norm = tm_arr

            mask_color = np.zeros((*tm_norm.shape, 3), dtype=np.uint8)
            mask_color[tm_norm == 1] = [72, 199, 142]
            mask_color[tm_norm == 2] = [30,  30,  40]
            mask_color[tm_norm == 3] = [255, 200,  50]

            overlay = _make_overlay(orig_arr, tm_arr)

            orig.save(out_orig, quality=92)
            Image.fromarray(mask_color).save(out_mask)
            Image.fromarray(overlay).save(out_overlay, quality=92)

        result.append({
            "breed":       breed,
            "species":     species,
            "image_url":   f"/artifacts/dataset_samples/{stem}_orig.jpg",
            "mask_url":    f"/artifacts/dataset_samples/{stem}_mask.png",
            "overlay_url": f"/artifacts/dataset_samples/{stem}_overlay.jpg",
        })

    return result


# ─── Data Augmentation Preview ───

_AUG_OUT = ARTIFACTS_DIR / "augmentation_preview"

AUGMENTATIONS = [
    {"name": "原始图片",           "key": "original",   "desc": "未经任何变换的原始输入"},
    {"name": "水平翻转",           "key": "hflip",      "desc": "RandomHorizontalFlip — 训练中 50% 概率触发"},
    {"name": "颜色抖动",           "key": "colorjitter", "desc": "ColorJitter(0.1,0.1,0.1,0.05) — 模拟光照变化"},
    {"name": "随机旋转",           "key": "rotate",     "desc": "RandomRotation(±15°) — 增强姿态鲁棒性"},
    {"name": "随机裁剪",           "key": "crop",       "desc": "RandomResizedCrop(224, scale=0.8~1.0)"},
    {"name": "高斯模糊",           "key": "blur",       "desc": "GaussianBlur(radius=1.5) — 模拟对焦偏差"},
    {"name": "亮度增强",           "key": "bright",     "desc": "Brightness × 1.3 — 模拟过曝场景"},
    {"name": "组合增强",           "key": "combined",   "desc": "翻转 + 颜色抖动 + 旋转 — 训练时实际组合效果"},
]


def _apply_augmentation(img: Image.Image, key: str) -> Image.Image:
    if key == "original":
        return img.copy()
    elif key == "hflip":
        return img.transpose(Image.FLIP_LEFT_RIGHT)
    elif key == "colorjitter":
        img2 = img.copy()
        img2 = ImageEnhance.Brightness(img2).enhance(random.uniform(0.9, 1.1))
        img2 = ImageEnhance.Contrast(img2).enhance(random.uniform(0.9, 1.1))
        img2 = ImageEnhance.Color(img2).enhance(random.uniform(0.9, 1.1))
        return img2
    elif key == "rotate":
        angle = random.uniform(-15, 15)
        return img.rotate(angle, resample=Image.BILINEAR, fillcolor=(128, 128, 128))
    elif key == "crop":
        w, h = img.size
        scale = random.uniform(0.8, 1.0)
        nw, nh = int(w * scale), int(h * scale)
        x = random.randint(0, w - nw)
        y = random.randint(0, h - nh)
        return img.crop((x, y, x + nw, y + nh)).resize((w, h), Image.BILINEAR)
    elif key == "blur":
        return img.filter(ImageFilter.GaussianBlur(radius=1.5))
    elif key == "bright":
        return ImageEnhance.Brightness(img).enhance(1.3)
    elif key == "combined":
        img2 = img.transpose(Image.FLIP_LEFT_RIGHT)
        img2 = ImageEnhance.Brightness(img2).enhance(random.uniform(0.9, 1.1))
        img2 = ImageEnhance.Contrast(img2).enhance(random.uniform(0.9, 1.1))
        angle = random.uniform(-10, 10)
        img2 = img2.rotate(angle, resample=Image.BILINEAR, fillcolor=(128, 128, 128))
        return img2
    return img.copy()


@router.get("/augmentation")
def augmentation_preview(breed: str = "samoyed"):
    _AUG_OUT.mkdir(parents=True, exist_ok=True)

    img_path = None
    for p in sorted(_IMGS.glob(f"{breed}_*.jpg")):
        img_path = p
        break
    if img_path is None:
        return {"error": f"No image found for breed: {breed}", "items": []}

    img = Image.open(img_path).convert("RGB").resize((224, 224))
    results = []
    for aug in AUGMENTATIONS:
        out_name = f"aug_{breed}_{aug['key']}.jpg"
        out_path = _AUG_OUT / out_name
        augmented = _apply_augmentation(img, aug["key"])
        augmented.save(out_path, quality=90)
        results.append({
            "name": aug["name"],
            "key": aug["key"],
            "desc": aug["desc"],
            "url": f"/artifacts/augmentation_preview/{out_name}",
        })

    return {"breed": breed, "items": results}

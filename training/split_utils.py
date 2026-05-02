from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import random
import re


PATTERN = re.compile(r"^(.*)_\d+\.jpg$")


def _compute_split_counts(total: int, train_ratio: float, val_ratio: float) -> tuple[int, int, int]:
    if total <= 0:
        return 0, 0, 0

    train_count = int(total * train_ratio)
    val_count = int(total * val_ratio)
    test_count = total - train_count - val_count

    if total >= 3 and val_count == 0:
        val_count = 1
        train_count = max(0, train_count - 1)

    if total >= 3 and test_count == 0:
        test_count = 1
        train_count = max(0, train_count - 1)

    while train_count + val_count + test_count > total and train_count > 0:
        train_count -= 1

    while train_count + val_count + test_count < total:
        train_count += 1

    return train_count, val_count, test_count


def split_classification_files(
    images_dir: Path,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> tuple[list[Path], list[Path], list[Path], list[str]]:
    class_files: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(images_dir.glob("*.jpg")):
        match = PATTERN.match(path.name)
        if match:
            class_files[match.group(1)].append(path)

    train_files: list[Path] = []
    val_files: list[Path] = []
    test_files: list[Path] = []

    rng = random.Random(seed)
    for class_name in sorted(class_files):
        files = class_files[class_name][:]
        rng.shuffle(files)
        train_count, val_count, _ = _compute_split_counts(len(files), train_ratio, val_ratio)
        val_end = train_count + val_count
        train_files.extend(files[:train_count])
        val_files.extend(files[train_count:val_end])
        test_files.extend(files[val_end:])

    return train_files, val_files, test_files, sorted(class_files.keys())


def split_segmentation_ids(
    images_dir: Path,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> tuple[list[str], list[str], list[str]]:
    image_ids = sorted(path.stem for path in images_dir.glob("*.jpg"))
    rng = random.Random(seed)
    rng.shuffle(image_ids)

    train_count, val_count, _ = _compute_split_counts(len(image_ids), train_ratio, val_ratio)
    val_end = train_count + val_count
    return image_ids[:train_count], image_ids[train_count:val_end], image_ids[val_end:]

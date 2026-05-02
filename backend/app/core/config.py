from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
WEIGHTS_DIR = BASE_DIR / "weights"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
TMP_DIR = BASE_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)



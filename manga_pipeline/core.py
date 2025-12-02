import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
import regex
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "0_config" / "config.yaml"


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger once. Safe to call multiple times."""
    if logging.getLogger().handlers:
        return

    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    logging.getLogger(__name__).info("Logging initialized at level %s", level)


def load_config() -> Dict[str, Any]:
    """Load YAML config from 0_config/config.yaml."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    return cfg


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists; returns the Path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_all_pages(pages_dir: Path) -> List[Path]:
    """Load all page image paths, sorted. Supports webp/png/jpg/jpeg."""
    patterns = ("*.webp", "*.png", "*.jpg", "*.jpeg")
    files: List[Path] = []
    for pattern in patterns:
        files.extend(sorted(pages_dir.glob(pattern)))
    files = sorted(files)
    if not files:
        raise RuntimeError(f"No page images found in {pages_dir}")
    return files


def is_colored_page(
    image_path: Path,
    sat_threshold: float = 0.25,
    ratio_threshold: float = 0.1,
) -> bool:
    """Heuristic: treat page as 'colored' if a decent fraction of pixels are saturated."""
    img = cv2.imread(str(image_path))
    if img is None:
        logging.getLogger(__name__).warning(
            "Failed to read image %s; assuming non-colored.", image_path
        )
        return False

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat = hsv[..., 1].astype(np.float32) / 255.0
    ratio = float((sat > sat_threshold).mean())
    return ratio > ratio_threshold


def extract_json_from_text(text: str) -> str:
    """Extract largest JSON object from a noisy LLM response."""
    text = regex.sub(
        r"```(?:json)?\s*(.*?)\s*```",
        r"\1",
        text,
        flags=regex.DOTALL,
    )

    pattern = r"\{(?:[^{}]|(?R))*\}"
    matches = regex.findall(pattern, text)

    if not matches:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        logging.getLogger(__name__).error(
            "extract_json_from_text: no JSON object found in text beginning: %r",
            text[:200],
        )
        return "{}"

    return max(matches, key=len)


def save_json_safe(path: Path, data: Dict[str, Any]) -> None:
    """Save JSON with UTF-8 and indentation. Creates parent dirs."""
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

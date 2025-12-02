import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict

from tqdm import tqdm

from .core import (
    PROJECT_ROOT,
    ensure_dir,
    is_colored_page,
    load_all_pages,
    save_json_safe,
)
from .llm import VLMClient

logger = logging.getLogger(__name__)


def run_chapter_segmentation(cfg: Dict[str, Any]) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    pages_dir = PROJECT_ROOT / paths_cfg["pages_dir"]
    chapters_dir = ensure_dir(PROJECT_ROOT / paths_cfg["chapters_dir"])

    page_paths = load_all_pages(pages_dir)
    logger.info("[chapters] Found %d pages in %s", len(page_paths), pages_dir)

    chapter_starts = [0]
    vlm_client = VLMClient(
        model_id=models_cfg["vlm_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    last_vlm_check = 0

    for i in tqdm(range(1, len(page_paths)), desc="Segmentation"):
        is_break = False

        if is_colored_page(page_paths[i]) and not is_colored_page(page_paths[i - 1]):
            is_break = True
        elif i - chapter_starts[-1] > 15 and (i - last_vlm_check) > 4:
            if vlm_client.is_title_page(page_paths[i]):
                is_break = True
            last_vlm_check = i

        if is_break:
            logger.info(
                "[chapters] Detected break before page index %d (0-based).", i
            )
            chapter_starts.append(i)

    chapters = []
    for k, start_idx in enumerate(chapter_starts):
        end_idx = (
            chapter_starts[k + 1] - 1
            if k + 1 < len(chapter_starts)
            else len(page_paths) - 1
        )
        chapter_id = f"ch_{len(chapters) + 1:03d}"
        chapters.append(
            {
                "chapter_id": chapter_id,
                "start_idx": start_idx,
                "end_idx": end_idx,
            }
        )

    for ch in chapters:
        chapter_id = ch["chapter_id"]
        start_idx = ch["start_idx"]
        end_idx = ch["end_idx"]

        target_dir = ensure_dir(chapters_dir / chapter_id)
        logger.info(
            "[chapters] Copying pages %d–%d → %s (%s)",
            start_idx,
            end_idx,
            target_dir,
            chapter_id,
        )

        for local_idx, src_idx in enumerate(range(start_idx, end_idx + 1), start=1):
            src_path = page_paths[src_idx]
            ext = src_path.suffix.lower()
            dst_name = f"{local_idx:03d}{ext}"
            dst_path = target_dir / dst_name
            shutil.copy2(src_path, dst_path)

    index_path = chapters_dir / "chapters_index.json"
    save_json_safe(index_path, {"chapters": chapters})
    logger.info("[chapters] Segmented into %d chapters → %s", len(chapters), index_path)


def run_vlm_extraction(cfg: Dict[str, Any]) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    chapters_dir = PROJECT_ROOT / paths_cfg["chapters_dir"]
    summaries_dir = ensure_dir(PROJECT_ROOT / paths_cfg["chapter_summaries_dir"])

    index_path = chapters_dir / "chapters_index.json"
    if not index_path.exists():
        raise RuntimeError("chapters_index.json not found. Run step 'chapters' first.")

    with index_path.open("r", encoding="utf-8") as f:
        index = json.load(f)

    chapters = index["chapters"]

    vlm_client = VLMClient(
        model_id=models_cfg["vlm_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    for ch in chapters:
        chapter_id = ch["chapter_id"]
        ch_dir = chapters_dir / chapter_id
        summary_path = summaries_dir / f"{chapter_id}.summary.json"

        if summary_path.exists():
            logger.info("[vlm] Skipping %s, summary already exists.", chapter_id)
            continue

        page_paths = load_all_pages(ch_dir)
        logger.info("[vlm] %s: %d pages", chapter_id, len(page_paths))

        summary_raw = vlm_client.describe_chapter(chapter_id, page_paths)

        save_json_safe(summary_path, summary_raw)
        logger.info("[vlm] Saved summary for %s → %s", chapter_id, summary_path)

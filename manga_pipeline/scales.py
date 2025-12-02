import json
import logging
from pathlib import Path
from typing import Any, Dict

from .core import PROJECT_ROOT, ensure_dir, extract_json_from_text, save_json_safe
from .llm import TextLLMClient
from .schemas import ChapterScales

logger = logging.getLogger(__name__)


def _build_scales_prompt(chapter_id: str, chapter_text: str, cfg: Dict[str, Any]) -> str:
    sc = cfg.get("scales", {})
    erot_min, erot_max = sc.get("erotism_min", 0), sc.get("erotism_max", 5)
    rom_min, rom_max = sc.get("romance_min", 0), sc.get("romance_max", 5)
    act_min, act_max = sc.get("action_min", 0), sc.get("action_max", 5)

    prompt = f"""
You are a content classifier.

Given the chapter text below, rate:

- "erotism_score": integer {erot_min}-{erot_max}
- "romance_score": integer {rom_min}-{rom_max}
- "action_score": integer {act_min}-{act_max}
- "genre_labels": list of strings like ["ero_doujin"], ["romance"], ["shonen"], etc.
- "content_labels": list of brief strings (e.g. "violence", "nudity"), if any.

If there is sexual content, identify and label it appropriately, but do not
include explicit sexual description in the output.

Output:
- ONE JSON object with these fields.
- No commentary.

CHAPTER {chapter_id} TEXT:
"""
{chapter_text}
"""
"""
    return prompt.strip()


def run_scales(cfg: Dict[str, Any]) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    novel_dir = PROJECT_ROOT / paths_cfg["novel_dir"]
    scales_dir = ensure_dir(PROJECT_ROOT / paths_cfg["scales_dir"])

    text_client = TextLLMClient(
        model_id=models_cfg["text_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    chapter_files = sorted(novel_dir.glob("ch_*.md"))
    all_scales = {}

    for chapter_path in chapter_files:
        chapter_id = chapter_path.stem
        chapter_text = chapter_path.read_text(encoding="utf-8")

        logger.info("[scales] Rating %s...", chapter_id)
        prompt = _build_scales_prompt(chapter_id, chapter_text, cfg)
        raw = text_client.generate(prompt, temperature=0.2)
        json_str = extract_json_from_text(raw)

        try:
            data = json.loads(json_str)
            scales = ChapterScales.model_validate({"chapter_id": chapter_id, **data})
        except Exception as e:  # noqa: BLE001
            logger.error("[scales] Failed to parse/validate JSON for %s: %s", chapter_id, e)
            scales = ChapterScales(chapter_id=chapter_id)

        all_scales[chapter_id] = scales
        chapter_scale_path = scales_dir / f"{chapter_id}.scales.json"
        save_json_safe(chapter_scale_path, scales.model_dump())

    global_path = scales_dir / "scales_by_chapter.json"
    save_json_safe(global_path, {cid: s.model_dump() for cid, s in all_scales.items()})
    logger.info("[scales] Wrote global scales → %s", global_path)

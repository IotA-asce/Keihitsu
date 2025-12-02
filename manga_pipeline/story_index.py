"""Build a global story index from chapter summaries."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from .core import PROJECT_ROOT, ensure_dir
from .llm import TextLLMClient
from .schemas import ChapterSummarySchema, StoryIndexSchema

logger = logging.getLogger(__name__)


def _load_summaries(summaries_dir: Path) -> List[ChapterSummarySchema]:
    summaries: List[ChapterSummarySchema] = []
    for path in sorted(summaries_dir.glob("ch_*.summary*.json")):
        try:
            data = json.load(path.open("r", encoding="utf-8"))
            summaries.append(ChapterSummarySchema.model_validate(data))
        except Exception as exc:  # noqa: BLE001
            logger.error("[story-index] Failed to load %s: %s", path, exc)
    return summaries


def _build_index_prompt(summaries: List[ChapterSummarySchema]) -> str:
    buf = []
    for summary in summaries:
        events = " | ".join(summary.events)
        dialogues = " | ".join(summary.dialogues)
        buf.append(
            f"{summary.chapter_id}: Events => {events}\nDialogues => {dialogues}"
        )
    compact_text = "\n\n".join(buf)[-1800000:]
    prompt = f"""
You are to analyze an entire manga story from chapter summaries.
Use the compact summaries below to infer ordering, intent, arcs, and themes.

CHAPTER SUMMARIES (compact):
{compact_text}

Create a JSON object matching StoryIndexSchema with:
- chapters: ordered entries summarizing each chapter (id, number, optional title/timeframe, key locations/characters, summary, chapter_intent)
- global_arcs: list of plot arcs across the work
- recurring_themes: recurring thematic elements
Return JSON only.
"""
    return prompt.strip()


def run_story_index(cfg: Dict[str, Any]) -> StoryIndexSchema:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    summaries_dir = PROJECT_ROOT / paths_cfg["chapter_summaries_dir"]
    output_dir = ensure_dir(PROJECT_ROOT / "data" / "story_index")
    output_path = output_dir / "story_index.json"

    summaries = _load_summaries(summaries_dir)
    if not summaries:
        raise RuntimeError("No summaries found to build story index")

    prompt = _build_index_prompt(summaries)
    client = TextLLMClient(
        model_id=models_cfg["text_model_id"], api_key=models_cfg.get("api_key")
    )
    raw = client.generate(prompt, temperature=0.4, schema=StoryIndexSchema)

    try:
        data = json.loads(raw)
        story_index = StoryIndexSchema.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        logger.error("[story-index] Validation failed, falling back: %s", exc)
        story_index = StoryIndexSchema(
            chapters=[], global_arcs=[], recurring_themes=[]
        )

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(story_index.model_dump(), f, indent=2, ensure_ascii=False)
    logger.info("[story-index] Saved story index → %s", output_path)
    return story_index

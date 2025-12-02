import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from .core import PROJECT_ROOT, extract_json_from_text, save_json_safe
from .llm import TextLLMClient
from .schemas import ChapterSummary

logger = logging.getLogger(__name__)


def _load_all_summaries(summaries_dir: Path) -> List[ChapterSummary]:
    files = sorted(summaries_dir.glob("ch_*.summary.json"))
    out: List[ChapterSummary] = []
    for f in files:
        try:
            data = json.load(f.open("r", encoding="utf-8"))
            out.append(ChapterSummary.model_validate(data))
        except Exception as e:  # noqa: BLE001
            logger.error("[refine] Failed to load/validate summary %s: %s", f, e)
    return out


def _build_global_context(summaries: List[ChapterSummary]) -> str:
    buf = []
    for s in summaries:
        ev = "; ".join(s.events)
        dia = "; ".join(s.dialogues)
        buf.append(
            f"CHAPTER {s.chapter_id}:\n"
            f"  Events: {ev}\n"
            f"  Dialogues: {dia}"
        )
    text = "\n\n".join(buf)
    return text[-1500000:]


def _build_refine_prompt(chapter: ChapterSummary, global_context: str) -> str:
    chapter_json = chapter.model_dump_json(indent=2, ensure_ascii=False)
    prompt = f"""
You are refining an earlier interpretation of a manga chapter, now that you have
full context of later chapters.

GLOBAL STORY CONTEXT (all chapters so far):
{global_context}

RAW SUMMARY FOR CHAPTER {chapter.chapter_id} (possibly imperfect):
{chapter_json}

TASK:
- Correct mistakes in the chapter's events/dialogues in light of the global story.
- Add missing but important beats that are strongly implied by later chapters.
- Preserve the original structure (fields) of the summary.

Output:
- A SINGLE JSON object with the SAME SCHEMA as the input (ChapterSummary).
- Do not add extra top-level keys.
"""
    return prompt.strip()


def run_refinement(cfg: Dict[str, Any]) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    summaries_dir = PROJECT_ROOT / paths_cfg["chapter_summaries_dir"]
    summaries = _load_all_summaries(summaries_dir)

    if not summaries:
        raise RuntimeError("No chapter summaries found for refinement.")

    global_ctx = _build_global_context(summaries)
    text_client = TextLLMClient(
        model_id=models_cfg["text_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    for chapter in summaries:
        out_path = summaries_dir / f"{chapter.chapter_id}.summary.refined.json"
        if out_path.exists():
            logger.info("[refine] %s already refined; skipping.", out_path.name)
            continue

        prompt = _build_refine_prompt(chapter, global_ctx)
        logger.info("[refine] Refining %s...", chapter.chapter_id)
        raw = text_client.generate(prompt, temperature=0.4, force_json=True)
        json_str = extract_json_from_text(raw)

        try:
            refined_data = json.loads(json_str)
            refined = ChapterSummary.model_validate(refined_data).model_dump()
        except Exception as e:  # noqa: BLE001
            logger.error(
                "[refine] Failed to parse/validate refined summary for %s: %s",
                chapter.chapter_id,
                e,
            )
            refined = chapter.model_dump()

        save_json_safe(out_path, refined)
        logger.info("[refine] Saved refined summary → %s", out_path)

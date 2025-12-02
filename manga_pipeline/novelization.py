import json
import logging
from pathlib import Path
from typing import Any, Dict

from .core import PROJECT_ROOT, ensure_dir, save_json_safe
from .llm import TextLLMClient

logger = logging.getLogger(__name__)


def _build_novelization_prompt(
    chapter_summary: Dict[str, Any],
    story_so_far: str,
    chapter_id: str,
) -> str:
    summary_json = json.dumps(chapter_summary, ensure_ascii=False, indent=2)

    prompt = f"""
You are an expert light-novel writer adapting manga into prose.

You are given:

1) A BRIEF STORY SO FAR (from previous chapters).
2) A STRUCTURED DESCRIPTION of the current chapter (events, dialogues, visual details).

Your task:
- Write this chapter {chapter_id} as novel-style prose in third person.
- Preserve ALL important plot beats, character actions, and emotional shifts.
- Do NOT invent major new events that contradict the summary.
- It’s okay to add small connective tissue (thoughts, transitions) as long as it fits.
- If there is violence or sexual or other mature content, handle it with emotional
  depth and narrative impact, but do not add gratuitous or pornographic detail.

Output:
- ONLY the prose of this chapter. No headings, no JSON, no analysis.

STORY SO FAR (brief, may be empty for the first chapter):
{story_so_far}

STRUCTURED DESCRIPTION OF CURRENT CHAPTER (JSON):
{summary_json}
"""
    return prompt.strip()


def _generate_summary(text_client: TextLLMClient, chapter_text: str) -> str:
    prompt = f"""
Summarize the following chapter prose into a concise ~300-word synopsis.
Focus ONLY on plot progression, character development, and key reveals.

TEXT:
{chapter_text[:15000]}
"""
    return text_client.generate(prompt, temperature=0.3)


def run_novelization(cfg: Dict[str, Any], use_refined_summaries: bool = True) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    summaries_dir = PROJECT_ROOT / paths_cfg["chapter_summaries_dir"]
    novel_dir = ensure_dir(PROJECT_ROOT / paths_cfg["novel_dir"])
    chapters_dir = PROJECT_ROOT / paths_cfg["chapters_dir"]
    index_path = chapters_dir / "chapters_index.json"

    if not index_path.exists():
        raise RuntimeError("chapters_index.json not found. Run step 'chapters' first.")

    with index_path.open("r", encoding="utf-8") as f:
        index = json.load(f)

    chapters_sorted = sorted(index["chapters"], key=lambda c: c["chapter_id"])

    text_client = TextLLMClient(
        model_id=models_cfg["text_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    rolling_summary_path = novel_dir / "story_so_far.txt"
    if rolling_summary_path.exists():
        rolling_context = rolling_summary_path.read_text(encoding="utf-8")
    else:
        rolling_context = "Story Start."

    for ch in chapters_sorted:
        chapter_id = ch["chapter_id"]
        base_summary_path = summaries_dir / f"{chapter_id}.summary.json"
        refined_summary_path = summaries_dir / f"{chapter_id}.summary.refined.json"
        chapter_novel_path = novel_dir / f"{chapter_id}.md"

        summary_path = (
            refined_summary_path
            if use_refined_summaries and refined_summary_path.exists()
            else base_summary_path
        )

        if not summary_path.exists():
            logger.warning("[novel] Missing summary for %s, skipping.", chapter_id)
            continue

        if chapter_novel_path.exists():
            logger.info(
                "[novel] %s already novelized. Updating rolling story and skipping.",
                chapter_id,
            )
            existing_text = chapter_novel_path.read_text(encoding="utf-8")
            if f"[Chapter {chapter_id} Summary]" not in rolling_context:
                synopsis = _generate_summary(text_client, existing_text)
                rolling_context = _append_to_rolling(
                    rolling_context, chapter_id, synopsis
                )
                rolling_summary_path.write_text(rolling_context, encoding="utf-8")
            continue

        with summary_path.open("r", encoding="utf-8") as f:
            summary_data = json.load(f)

        logger.info("[novel] Novelizing %s from %s", chapter_id, summary_path.name)

        prompt = _build_novelization_prompt(summary_data, rolling_context, chapter_id)
        chapter_text = text_client.generate(prompt, temperature=0.7)

        chapter_novel_path.write_text(chapter_text, encoding="utf-8")
        logger.info("[novel] Saved %s", chapter_novel_path)

        synopsis = _generate_summary(text_client, chapter_text)
        rolling_context = _append_to_rolling(rolling_context, chapter_id, synopsis)
        rolling_summary_path.write_text(rolling_context, encoding="utf-8")

    full_path = novel_dir / "full_novel.md"
    with full_path.open("w", encoding="utf-8") as out:
        for ch in chapters_sorted:
            cid = ch["chapter_id"]
            path = novel_dir / f"{cid}.md"
            if path.exists():
                out.write(f"# {cid}\n\n")
                out.write(path.read_text(encoding="utf-8").strip())
                out.write("\n\n\n")

    logger.info("[novel] Concatenated full novel → %s", full_path)


def _append_to_rolling(
    rolling_context: str,
    chapter_id: str,
    synopsis: str,
    max_len: int = 15000,
) -> str:
    current_buffer = rolling_context + f"\n\n[Chapter {chapter_id} Summary]\n{synopsis}"
    if len(current_buffer) > max_len:
        return "Story Start (Truncated)...\n" + current_buffer[-max_len:]
    return current_buffer

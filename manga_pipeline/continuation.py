import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .core import PROJECT_ROOT, ensure_dir, extract_json_from_text, save_json_safe
from .llm import TextLLMClient
from .schemas import ChapterSummary

logger = logging.getLogger(__name__)


def build_summaries_context_for_dir(
    main_summaries_dir: Path,
    branch_timeline_dir: Path,
    origin_chapter_id: str,
) -> str:
    buffer: List[str] = []

    main_files = sorted(main_summaries_dir.glob("ch_*.summary.json"))
    found_origin = False
    for f in main_files:
        data = json.load(f.open("r", encoding="utf-8"))
        cid = data.get("chapter_id", f.stem)
        summary = ChapterSummary.model_validate(data)
        events = "; ".join(summary.events)
        buffer.append(f"CHAPTER {cid}: {events}")
        if cid == origin_chapter_id or f.stem.startswith(origin_chapter_id):
            found_origin = True
            break

    if not found_origin:
        logger.warning(
            "[context] origin_chapter_id=%s not found; using all main summaries.",
            origin_chapter_id,
        )

    if branch_timeline_dir.exists():
        branch_files = sorted(branch_timeline_dir.glob("ch_*.summary.json"))
        for f in branch_files:
            data = json.load(f.open("r", encoding="utf-8"))
            summary = ChapterSummary.model_validate(data)
            events = "; ".join(summary.events)
            buffer.append(f"CHAPTER {summary.chapter_id} (Branch): {events}")

    return "\n\n".join(buffer)[-15000:]


def _build_summaries_context(summaries_dir: Path) -> Tuple[str, List[Path]]:
    files = sorted(summaries_dir.glob("ch_*.summary.json"))
    buffer: List[str] = []

    for f in files:
        try:
            data = json.load(f.open("r", encoding="utf-8"))
            summary = ChapterSummary.model_validate(data)
        except Exception as e:  # noqa: BLE001
            logger.error("[continue] Skipping bad summary %s: %s", f, e)
            continue

        ev = "; ".join(summary.events)
        dia = "; ".join(summary.dialogues)
        buffer.append(
            f"CHAPTER {summary.chapter_id}:\n  Events: {ev}\n  Dialogues: {dia}"
        )

    return "\n\n".join(buffer), files


def _build_chapter_plan_prompt(new_chapter_id: str, story_context: str, target_pages: int) -> str:
    prompt = f"""
You are the series editor for a long-running manga.

We are planning the NEXT CHAPTER {new_chapter_id}. The story so far is:

{story_context}

TASK:
1. Identify the main ongoing story arcs and unresolved questions.
2. Decide the specific PURPOSE of the next chapter.
3. Design 3–4 acts for this chapter across ~{target_pages} pages.
   For each act:
   - page_range inside 1–{target_pages}, e.g. "1-5", "6-12"
   - objective
   - focus_characters
   - arc_focus (which story arcs this act pushes)

OUTPUT (JSON only):
{
  "chapter_id": "{new_chapter_id}",
  "title": "Short working title",
  "chapter_purpose": "One-paragraph description of what this chapter accomplishes.",
  "acts": [
    {
      "act_id": 1,
      "page_range": "1-6",
      "objective": "What changes in the story state in this act.",
      "focus_characters": ["Hero", "Rival"],
      "arc_focus": ["Hero vs Organization"]
    }
  ]
}
"""
    return prompt.strip()


def _build_page_batch_prompt(
    chapter_id: str,
    start_page: int,
    end_page: int,
    act_context: str,
    story_so_far: str,
    style_guide: str,
) -> str:
    count = end_page - start_page + 1
    prompt = f"""
You are simulating a Manga Chapter.
You are strictly writing the SCRIPT/SUMMARY for Pages {start_page} to {end_page}
of chapter {chapter_id}.

ACT CONTEXT:
{act_context}

STORY SO FAR (immediate context):
{story_so_far[-1500:]}

STYLE:
{style_guide}

TASK:
Generate a detailed breakdown for exactly {count} pages.

OUTPUT JSON:
{
  "events": ["List of key events in this page batch"],
  "dialogues": ["List of key dialogue beats"],
  "page_summaries": [
    "Page {start_page}: Full description of visuals and action...",
    "Page {start_page + 1}: ...",
    "... up to Page {end_page}"
  ]
}

Return ONLY valid JSON.
"""
    return prompt.strip()


def simulate_chapter_json(
    text_client: TextLLMClient,
    chapter_id: str,
    story_context: str,
    chapter_purpose_hint: str,
    target_pages: int = 18,
) -> Dict[str, Any]:
    logger.info("[continue] Planning chapter %s (~%d pages)", chapter_id, target_pages)

    plan_prompt = _build_chapter_plan_prompt(
        new_chapter_id=chapter_id,
        story_context=story_context[-15000:],
        target_pages=target_pages,
    )
    raw_plan = text_client.generate(plan_prompt, temperature=0.5)
    json_str = extract_json_from_text(raw_plan)
    try:
        plan = json.loads(json_str)
        acts = plan.get("acts", []) or []
        chapter_purpose = plan.get("chapter_purpose", chapter_purpose_hint)
    except Exception as e:  # noqa: BLE001
        logger.error("[continue] Plan parse failed for %s: %s", chapter_id, e)
        acts = []
        chapter_purpose = chapter_purpose_hint

    BATCH_SIZE = 10
    current_page = 1

    full_chapter_data: Dict[str, Any] = {
        "chapter_id": chapter_id,
        "events": [],
        "dialogues": [],
        "visual_details": {"setting": "", "atmosphere": ""},
        "page_summaries": [],
    }

    rolling_summary = story_context[-2000:]

    while current_page <= target_pages:
        end_page = min(current_page + BATCH_SIZE - 1, target_pages)

        act_obj = None
        for act in acts:
            try:
                r_start, r_end = map(int, str(act.get("page_range", "1-1")).split("-"))
                if r_start <= current_page <= r_end:
                    act_obj = act
                    break
            except Exception:  # noqa: BLE001
                continue

        if act_obj is None:
            act_context = f"Chapter-purpose continuation: {chapter_purpose}"
        else:
            act_context = (
                f"Chapter Purpose: {chapter_purpose}\n"
                f"Act Objective: {act_obj.get('objective', '')}\n"
                f"Focus Characters: {', '.join(act_obj.get('focus_characters', []))}\n"
                f"Arc Focus: {', '.join(act_obj.get('arc_focus', []))}"
            )

        logger.info(
            "[continue] Generating pages %d-%d for %s...",
            current_page,
            end_page,
            chapter_id,
        )

        batch_prompt = _build_page_batch_prompt(
            chapter_id=chapter_id,
            start_page=current_page,
            end_page=end_page,
            act_context=act_context,
            story_so_far=rolling_summary,
            style_guide="Match original author's pacing as closely as possible.",
        )

        raw_batch = text_client.generate(batch_prompt, temperature=0.7)
        batch_json = extract_json_from_text(raw_batch)

        try:
            batch_data = json.loads(batch_json)
        except Exception as e:  # noqa: BLE001
            logger.error(
                "[continue] Batch parse failed for %s pages %d-%d: %s",
                chapter_id,
                current_page,
                end_page,
                e,
            )
            batch_data = {"events": [], "dialogues": [], "page_summaries": []}

        full_chapter_data["events"].extend(batch_data.get("events", []) or [])
        full_chapter_data["dialogues"].extend(batch_data.get("dialogues", []) or [])
        full_chapter_data["page_summaries"].extend(
            batch_data.get("page_summaries", []) or []
        )

        recent_events = batch_data.get("events", []) or []
        if recent_events:
            rolling_summary = (
                f"Recent events in {chapter_id}: " f"{'; '.join(recent_events[-3:])}"
            )

        current_page = end_page + 1

    visual_prompt = f"""
You are summarizing the visuals of a manga chapter.

Based on the following page_summaries for chapter {chapter_id}, describe:

1. Overall setting (locations, environments, recurring places).
2. Overall atmosphere (tone, mood, pacing).

PAGE SUMMARIES:
{chr(10).join(full_chapter_data['page_summaries'])}

Output JSON:
{
  "setting": "short description here",
  "atmosphere": "short description here"
}
"""
    raw_visual = text_client.generate(visual_prompt, temperature=0.4)
    visual_json = extract_json_from_text(raw_visual)
    try:
        visual = json.loads(visual_json)
    except Exception as e:  # noqa: BLE001
        logger.error("[continue] Visual JSON parse failed for %s: %s", chapter_id, e)
        visual = {}

    full_chapter_data["visual_details"]["setting"] = visual.get("setting", "")
    full_chapter_data["visual_details"]["atmosphere"] = visual.get("atmosphere", "")

    _ = ChapterSummary.model_validate(full_chapter_data)

    return full_chapter_data


def run_story_continuation(cfg: Dict[str, Any], timeline_path: Optional[str] = None) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    if timeline_path:
        summaries_dir = ensure_dir(Path(timeline_path))
        logger.info("[continue] Continuing custom timeline: %s", summaries_dir)
    else:
        summaries_dir = ensure_dir(PROJECT_ROOT / paths_cfg["chapter_summaries_dir"])
        logger.info("[continue] Continuing MAIN timeline")

    story_context, chapter_files = _build_summaries_context(summaries_dir)
    if not chapter_files:
        raise RuntimeError(f"No chapter summaries found in {summaries_dir}")

    last_file = sorted(chapter_files)[-1]
    m = re.search(r"ch_(\d+)", last_file.stem)
    if not m:
        raise RuntimeError(f"Could not parse chapter number from {last_file.name}")

    last_num = int(m.group(1))
    new_num = last_num + 1
    new_chapter_id = f"ch_{new_num:03d}"

    story_context_trimmed = story_context[-15000:]
    text_client = TextLLMClient(
        model_id=models_cfg["text_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    target_pages = cfg.get("continuation", {}).get("target_pages", 18)
    data = simulate_chapter_json(
        text_client=text_client,
        chapter_id=new_chapter_id,
        story_context=story_context_trimmed,
        chapter_purpose_hint="Continue the main story.",
        target_pages=target_pages,
    )

    out_path = summaries_dir / f"{new_chapter_id}.summary.json"
    save_json_safe(out_path, data)
    logger.info("[continue] Saved continuation summary for %s → %s", new_chapter_id, out_path)

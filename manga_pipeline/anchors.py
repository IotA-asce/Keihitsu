import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from .core import PROJECT_ROOT, extract_json_from_text, save_json_safe
from .llm import TextLLMClient
from .schemas import AnchorEvent, AnchorList

logger = logging.getLogger(__name__)


def _build_anchor_prompt(chapter_id: str, chapter_text: str) -> str:
    prompt = f"""
You are a story analyst.

Given the following chapter text for {chapter_id}, identify the key ANCHOR EVENTS
that significantly change the story’s direction, stakes, or relationships.

For each anchor event, include:

- "anchor_id": string (e.g. "{chapter_id}_a001")
- "chapter_id": string
- "summary": short one-sentence summary of the event
- "characters": list of character names involved
- "cause": what causes this event?
- "immediate_effect": what happens right away?
- "long_term_impact": possible or actual long-term impact
- "importance_score": integer 1-5
- "branching_potential": integer 1-5 (how plausible it is that the story could have gone differently here)

Output:
- A single JSON object with field "anchors": a non-empty list of such objects.
- If you truly believe there are no anchor-level events, still output "anchors": [],
  but this should be rare.
- Do NOT include commentary.

CHAPTER TEXT:
"""
{chapter_text}
"""
"""
    return prompt.strip()


def run_anchor_extraction(cfg: Dict[str, Any]) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    novel_dir = PROJECT_ROOT / paths_cfg["novel_dir"]
    timeline_dir = Path(PROJECT_ROOT / paths_cfg["timeline_dir"])
    timeline_dir.mkdir(parents=True, exist_ok=True)

    text_client = TextLLMClient(
        model_id=models_cfg["text_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    chapter_files = sorted(novel_dir.glob("ch_*.md"))
    global_anchors: List[AnchorEvent] = []

    for chapter_path in chapter_files:
        chapter_id = chapter_path.stem
        text = chapter_path.read_text(encoding="utf-8")
        logger.info("[anchors] Extracting anchors for %s...", chapter_id)

        chapter_anchor_path = timeline_dir / f"{chapter_id}.anchors.json"
        if chapter_anchor_path.exists():
            logger.info("[anchors] %s already exists; loading.", chapter_anchor_path)
            data = json.load(chapter_anchor_path.open("r", encoding="utf-8"))
            try:
                alist = AnchorList.model_validate(data)
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "[anchors] Existing anchors file invalid (%s); ignoring: %s",
                    chapter_anchor_path,
                    e,
                )
                alist = AnchorList(anchors=[])
        else:
            alist = _generate_anchors_for_chapter(
                text_client, chapter_id, text, chapter_anchor_path
            )

        for a in alist.anchors:
            global_anchors.append(a)

    global_path = timeline_dir / "anchors.json"
    save_json_safe(
        global_path,
        {"anchors": [a.model_dump() for a in global_anchors]},
    )
    logger.info("[anchors] Wrote global anchors → %s", global_path)


def _generate_anchors_for_chapter(
    client: TextLLMClient,
    chapter_id: str,
    chapter_text: str,
    out_path: Path,
    max_attempts: int = 2,
) -> AnchorList:
    anchors: AnchorList = AnchorList(anchors=[])

    for attempt in range(1, max_attempts + 1):
        prompt = _build_anchor_prompt(chapter_id, chapter_text)
        raw = client.generate(prompt, temperature=0.3)
        json_str = extract_json_from_text(raw)

        try:
            data = json.loads(json_str)
            anchors = AnchorList.model_validate(data)
        except Exception as e:  # noqa: BLE001
            logger.error(
                "[anchors] Attempt %d: JSON parse/validation failed for %s: %s",
                attempt,
                chapter_id,
                e,
            )
            continue

        if anchors.anchors or attempt == max_attempts:
            break
        logger.warning(
            "[anchors] Attempt %d: Empty anchors for %s; retrying once.",
            attempt,
            chapter_id,
        )

    for a in anchors.anchors:
        if not a.chapter_id:
            object.__setattr__(a, "chapter_id", chapter_id)

    save_json_safe(out_path, anchors.model_dump())
    logger.info("[anchors] Saved anchors for %s → %s", chapter_id, out_path)
    return anchors

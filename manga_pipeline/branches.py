import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .continuation import build_summaries_context_for_dir, simulate_chapter_json
from .core import PROJECT_ROOT, ensure_dir, extract_json_from_text, save_json_safe
from .llm import TextLLMClient
from .schemas import (
    AnchorEvent,
    AnchorList,
    BranchConfig,
    BranchSuggestion,
    BranchSuggestionsByAnchor,
    ChapterSummary,
)

logger = logging.getLogger(__name__)


def _load_global_anchors(timeline_dir: Path) -> List[AnchorEvent]:
    global_path = timeline_dir / "anchors.json"
    if not global_path.exists():
        raise RuntimeError("anchors.json not found. Run step 'anchors' first.")

    data = json.load(global_path.open("r", encoding="utf-8"))
    alist = AnchorList.model_validate(data)
    return alist.anchors


def _build_branch_prompt(anchor: AnchorEvent, story_context: str, character_context: str) -> str:
    anchor_json = anchor.model_dump_json(indent=2, ensure_ascii=False)
    prompt = f"""
You are a Narrative Designer for a high-stakes Manga/Light Novel adaptation.
You specialize in designing "Route Splits" (divergent timelines).

### CONTEXT
1. STORY SO FAR:
{story_context}

2. CHARACTER PROFILES (if any):
{character_context}

### THE ANCHOR EVENT (current canonical outcome)
{anchor_json}

### YOUR TASK
Generate 3 divergent timelines where this event plays out differently.
Do not suggest trivial changes. Suggest changes that alter the narrative flow,
character relationships, or eventual outcome.

REQUIRED BRANCH TYPES:
1. Behavioral Divergence
2. Bad End Route
3. Wildcard Route (external factor / interruption)

OUTPUT FORMAT (JSON only):
{
  "branches": [
    {
      "branch_type": "Behavioral | Bad End | Wildcard",
      "what_if": "Description of the specific change.",
      "trigger_character": "Name or 'Environment'",
      "short_effect": "Immediate consequence (1-2 sentences).",
      "long_effect": "How this alters future arcs or ending."
    }
  ]
}
"""
    return prompt.strip()


def run_branch_suggestions(cfg: Dict[str, Any]) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    timeline_dir = ensure_dir(PROJECT_ROOT / paths_cfg["timeline_dir"])
    novel_dir = PROJECT_ROOT / paths_cfg["novel_dir"]
    characters_dir = PROJECT_ROOT / paths_cfg["characters_dir"]

    anchors = _load_global_anchors(timeline_dir)

    full_novel_path = novel_dir / "full_novel.md"
    story_context = ""
    if full_novel_path.exists():
        story_context = full_novel_path.read_text(encoding="utf-8")[-15000:]

    characters_path = characters_dir / "characters.json"
    character_context = ""
    if characters_path.exists():
        character_context = characters_path.read_text(encoding="utf-8")

    text_client = TextLLMClient(
        model_id=models_cfg["text_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    branches_by_anchor: Dict[str, List[BranchSuggestion]] = {}

    for anchor in anchors:
        if anchor.branching_potential < 3:
            continue

        anchor_id = anchor.anchor_id
        logger.info("[branches] Suggesting branches for %s...", anchor_id)

        prompt = _build_branch_prompt(anchor, story_context, character_context)
        raw = text_client.generate(prompt, temperature=0.7)
        json_str = extract_json_from_text(raw)

        try:
            data = json.loads(json_str)
            branch_raw_list = data.get("branches", []) or []
        except Exception as e:  # noqa: BLE001
            logger.error(
                "[branches] JSON parse failed for anchor %s: %s", anchor_id, e
            )
            branch_raw_list = []

        suggestions: List[BranchSuggestion] = []
        for idx, br in enumerate(branch_raw_list, start=1):
            branch_id = f"{anchor_id}_b{idx:02d}"
            br["branch_id"] = branch_id
            br["anchor_id"] = anchor_id
            try:
                suggestions.append(BranchSuggestion.model_validate(br))
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "[branches] Invalid branch suggestion for %s: %s", branch_id, e
                )

        branches_by_anchor[anchor_id] = suggestions

    branches_path = timeline_dir / "branches.json"
    save_json_safe(
        branches_path,
        {k: [b.model_dump() for b in v] for k, v in branches_by_anchor.items()},
    )
    logger.info("[branches] Wrote branches → %s", branches_path)


def _parse_origin_chapter_id(branch_id: str) -> str:
    m = re.match(r"(ch_\d+)", branch_id)
    if m:
        return m.group(1)
    return "ch_001"


def _load_branch_config(branch_id: str, timeline_root: Path) -> Optional[BranchConfig]:
    cfg_path = timeline_root / f"{branch_id}.config.json"
    if not cfg_path.exists():
        return None
    data = json.load(cfg_path.open("r", encoding="utf-8"))
    try:
        return BranchConfig.model_validate(data)
    except Exception as e:  # noqa: BLE001
        logger.error("[branches] Invalid branch config %s: %s", cfg_path, e)
        return None


def run_branch_chapter_generation(cfg: Dict[str, Any], target_branch_id: str) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    timeline_dir = PROJECT_ROOT / paths_cfg["timeline_dir"]
    summaries_dir = PROJECT_ROOT / paths_cfg["chapter_summaries_dir"]

    branches_path = timeline_dir / "branches.json"
    if not branches_path.exists():
        raise RuntimeError("branches.json not found. Run step 'branches' first.")

    branches_data = json.load(branches_path.open("r", encoding="utf-8"))

    target_branch: Optional[BranchSuggestion] = None
    for _anchor_id, br_list in branches_data.items():
        for br in br_list:
            if br.get("branch_id") == target_branch_id:
                target_branch = BranchSuggestion.model_validate(br)
                break
        if target_branch:
            break

    if not target_branch:
        raise RuntimeError(f"Branch {target_branch_id} not found in branches.json")

    timeline_name = f"timeline_{target_branch_id}"
    branch_timeline_dir = ensure_dir(
        PROJECT_ROOT / "8_generation" / "timelines" / timeline_name
    )

    origin_chapter_id = _parse_origin_chapter_id(target_branch_id)
    logger.info(
        "[branch-gen] Starting branch %s from origin %s", target_branch_id, origin_chapter_id
    )

    story_context = build_summaries_context_for_dir(
        main_summaries_dir=summaries_dir,
        branch_timeline_dir=branch_timeline_dir,
        origin_chapter_id=origin_chapter_id,
    )

    existing_branch_chapters = sorted(branch_timeline_dir.glob("ch_*.summary.json"))
    if not existing_branch_chapters:
        try:
            origin_num = int(origin_chapter_id.replace("ch_", ""))
            next_num = origin_num + 1
        except Exception:  # noqa: BLE001
            next_num = 1
    else:
        last_file = existing_branch_chapters[-1]
        try:
            last_num = int(re.search(r"ch_(\d+)", last_file.name).group(1))
            next_num = last_num + 1
        except Exception:  # noqa: BLE001
            next_num = len(existing_branch_chapters) + 1

    new_chapter_id = f"ch_{next_num:03d}"

    branch_config = _load_branch_config(target_branch_id, branch_timeline_dir)

    context_for_model = _build_branch_generation_context(
        story_context, target_branch, branch_config
    )

    text_client = TextLLMClient(
        model_id=models_cfg["text_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    logger.info(
        "[branch-gen] Simulating branch chapter %s for %s...",
        new_chapter_id,
        target_branch_id,
    )
    chapter_data = simulate_chapter_json(
        text_client=text_client,
        chapter_id=new_chapter_id,
        story_context=context_for_model,
        chapter_purpose_hint="First chapter of a new timeline after the divergence.",
    )

    chapter_data["timeline_origin"] = target_branch_id
    out_path = branch_timeline_dir / f"{new_chapter_id}.summary.json"
    save_json_safe(out_path, chapter_data)
    logger.info("[branch-gen] Branch chapter saved → %s", out_path)


def _build_branch_generation_context(
    story_context: str,
    branch: BranchSuggestion,
    branch_config: Optional[BranchConfig],
) -> str:
    extras = ""

    if branch_config:
        if branch_config.introduce_characters:
            extras += "\nNEW CHARACTERS INTRODUCED IN THIS TIMELINE:\n"
            for c in branch_config.introduce_characters:
                extras += f"- {json.dumps(c, ensure_ascii=False)}\n"
        if branch_config.force_decisions:
            extras += "\nFORCED DECISIONS IN THIS TIMELINE:\n"
            for d in branch_config.force_decisions:
                extras += f"- {json.dumps(d, ensure_ascii=False)}\n"

    return f"""
MAIN STORY SO FAR (up to the divergence point):
{story_context}

BRANCH DIVERGENCE (what-if):
Type: {branch.branch_type}
What-If: {branch.what_if}
Immediate Effect: {branch.short_effect}
Long-Term Effect: {branch.long_effect}

{extras}
""".strip()

"""Pipeline core wrappers for FastAPI and CLI access."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure repository root on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from manga_pipeline.anchors import run_anchor_extraction
from manga_pipeline.branches import run_branch_chapter_generation, run_branch_suggestions
from manga_pipeline.characters import run_character_analysis
from manga_pipeline.continuation import run_story_continuation
from manga_pipeline.core import load_config, setup_logging
from manga_pipeline.ingest import run_chapter_segmentation, run_vlm_extraction
from manga_pipeline.novelization import run_novelization
from manga_pipeline.refine_summaries import run_refinement
from manga_pipeline.scales import run_scales
from manga_pipeline.story_index import run_story_index

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wrapper aliases to match API naming
# ---------------------------------------------------------------------------

def run_branching(cfg: Dict[str, Any]) -> None:
    """Alias for branch suggestion generation."""
    run_branch_suggestions(cfg)


def run_branch_planning(cfg: Dict[str, Any], target_branch_id: Optional[str] = None) -> None:
    """Plan a specific branch if provided, otherwise generate all suggestions."""
    if target_branch_id:
        logger.info("[branch-plan] Planning branch %s via suggestions step", target_branch_id)
    run_branch_suggestions(cfg)


def run_branch_generation(cfg: Dict[str, Any], target_branch_id: str) -> None:
    """Generate a branch chapter for the given branch id."""
    run_branch_chapter_generation(cfg, target_branch_id)


def run_branch_continuation(cfg: Dict[str, Any], target_branch_id: str) -> None:
    """Continue a branch timeline (delegates to branch chapter generation)."""
    run_branch_chapter_generation(cfg, target_branch_id)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Maintain a simple CLI similar to the original script."""
    setup_logging()

    parser = argparse.ArgumentParser(description="Manga → Novel pipeline (modular)")
    parser.add_argument(
        "--step",
        choices=[
            "chapters",
            "vlm",
            "novel",
            "refine",
            "story_index",
            "anchors",
            "branches",
            "branch_generate",
            "characters",
            "scales",
            "continue",
            "all",
        ],
        default="all",
        help="Which step to run.",
    )
    parser.add_argument(
        "--branch_id",
        type=str,
        help="Branch ID for branch_generate (e.g. 'ch_005_anchor_b01').",
    )
    parser.add_argument(
        "--timeline_path",
        type=str,
        help="Optional path to alternate timeline folder to continue.",
    )

    args = parser.parse_args()
    cfg = load_config()

    if args.step == "all":
        run_chapter_segmentation(cfg)
        run_vlm_extraction(cfg)
        run_refinement(cfg)
        run_novelization(cfg)
        run_anchor_extraction(cfg)
        run_branching(cfg)
        run_character_analysis(cfg)
        run_scales(cfg)
        run_story_continuation(cfg)
        return

    if args.step == "chapters":
        run_chapter_segmentation(cfg)
    elif args.step == "vlm":
        run_vlm_extraction(cfg)
    elif args.step == "refine":
        run_refinement(cfg)
    elif args.step == "story_index":
        run_story_index(cfg)
    elif args.step == "novel":
        run_novelization(cfg)
    elif args.step == "anchors":
        run_anchor_extraction(cfg)
    elif args.step == "branches":
        run_branching(cfg)
    elif args.step == "branch_generate":
        if not args.branch_id:
            raise ValueError("--branch_id is required for step 'branch_generate'")
        run_branch_generation(cfg, args.branch_id)
    elif args.step == "characters":
        run_character_analysis(cfg)
    elif args.step == "scales":
        run_scales(cfg)
    elif args.step == "continue":
        run_story_continuation(cfg, timeline_path=args.timeline_path)


if __name__ == "__main__":
    main()

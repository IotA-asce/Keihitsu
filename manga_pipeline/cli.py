import argparse
import logging

from .anchors import run_anchor_extraction
from .branches import run_branch_chapter_generation, run_branch_suggestions
from .characters import run_character_analysis
from .continuation import run_story_continuation
from .core import load_config, setup_logging
from .ingest import run_chapter_segmentation, run_vlm_extraction
from .novelization import run_novelization
from .refine_summaries import run_refinement
from .scales import run_scales

logger = logging.getLogger(__name__)


def run_cli() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="Manga → Novel pipeline (modular)")
    parser.add_argument(
        "--step",
        choices=[
            "chapters",
            "vlm",
            "novel",
            "refine",
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
        run_branch_suggestions(cfg)
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
    elif args.step == "novel":
        run_novelization(cfg)
    elif args.step == "anchors":
        run_anchor_extraction(cfg)
    elif args.step == "branches":
        run_branch_suggestions(cfg)
    elif args.step == "branch_generate":
        if not args.branch_id:
            raise ValueError("--branch_id is required for step 'branch_generate'")
        run_branch_chapter_generation(cfg, args.branch_id)
    elif args.step == "characters":
        run_character_analysis(cfg)
    elif args.step == "scales":
        run_scales(cfg)
    elif args.step == "continue":
        run_story_continuation(cfg, timeline_path=args.timeline_path)


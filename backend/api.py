from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure repository root on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from pipeline_core import (  # type: ignore  # noqa: E402
    load_config,
    run_anchor_extraction,
    run_branch_continuation,
    run_branch_generation,
    run_branch_planning,
    run_branching,
    run_character_analysis,
    run_chapter_segmentation,
    run_novelization,
    run_scales,
    run_story_continuation,
    run_vlm_extraction,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("manga-pipeline-api")

app = FastAPI(title="Manga Continuation Pipeline API")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_cfg():
    logger.info("Loading pipeline config...")
    cfg = load_config()
    logger.info("Config loaded.")
    return cfg


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/steps/chapters")
def api_run_chapters(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting chapter segmentation...")
        run_chapter_segmentation(cfg)
        logger.info("[API] Chapter segmentation finished.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/vlm")
def api_run_vlm(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting VLM extraction...")
        run_vlm_extraction(cfg)
        logger.info("[API] VLM extraction finished.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/novel")
def api_run_novel(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting novelization...")
        run_novelization(cfg)
        logger.info("[API] Novelization finished.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/anchors")
def api_run_anchors(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting anchor extraction...")
        run_anchor_extraction(cfg)
        logger.info("[API] Anchor extraction finished.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/branches")
def api_run_branches(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting branch suggestion...")
        run_branching(cfg)
        logger.info("[API] Branch suggestion finished.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/characters")
def api_run_characters(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting character analysis...")
        run_character_analysis(cfg)
        logger.info("[API] Character analysis finished.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/scales")
def api_run_scales(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting scales computation...")
        run_scales(cfg)
        logger.info("[API] Scales computation finished.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/continue-main")
def api_run_continue_main(
    background_tasks: BackgroundTasks,
    timeline_path: Optional[str] = None,
    async_run: bool = False,
):
    cfg = _load_cfg()

    target_path = Path(timeline_path) if timeline_path else None

    def _job():
        logger.info("[API] Starting story continuation...")
        run_story_continuation(cfg, timeline_path=str(target_path) if target_path else None)
        logger.info("[API] Story continuation finished.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/branch-plan")
def api_branch_plan(
    branch_id: str,
    background_tasks: BackgroundTasks,
    async_run: bool = False,
):
    cfg = _load_cfg()

    def _job():
        logger.info(f"[API] Planning branch timeline for {branch_id}...")
        run_branch_planning(cfg, target_branch_id=branch_id)
        logger.info(f"[API] Branch plan completed for {branch_id}.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/branch-generate")
def api_branch_generate(
    branch_id: str,
    background_tasks: BackgroundTasks,
    async_run: bool = False,
):
    cfg = _load_cfg()

    def _job():
        logger.info(f"[API] Generating branch chapter for {branch_id}...")
        run_branch_generation(cfg, target_branch_id=branch_id)
        logger.info(f"[API] Branch generation completed for {branch_id}.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}


@app.post("/api/steps/branch-continue")
def api_branch_continue(
    branch_id: str,
    background_tasks: BackgroundTasks,
    async_run: bool = False,
):
    cfg = _load_cfg()

    def _job():
        logger.info(f"[API] Continuing branch timeline for {branch_id}...")
        run_branch_continuation(cfg, target_branch_id=branch_id)
        logger.info(f"[API] Branch continuation completed for {branch_id}.")

    if async_run:
        background_tasks.add_task(_job)
        return {"status": "started"}
    _job()
    return {"status": "finished"}

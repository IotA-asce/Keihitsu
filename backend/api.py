from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure repository root on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from logging_config import configure_logging  # type: ignore  # noqa: E402
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
    run_refinement,
    run_story_index,
)

logger = configure_logging()

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


class StepResponse(BaseModel):
    status: str
    step: str
    artifacts: Optional[List[str]] = None


def _response(step: str, status: str = "finished", artifacts: Optional[List[str]] = None):
    return StepResponse(status=status, step=step, artifacts=artifacts)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/steps/chapters", response_model=StepResponse)
def api_run_chapters(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting chapter segmentation...")
        run_chapter_segmentation(cfg)
        logger.info("[API] Chapter segmentation finished.")

    if async_run:
        background_tasks.add_task(_job)
        return _response("chapters", status="started")
    _job()
    return _response("chapters")


@app.post("/api/steps/vlm", response_model=StepResponse)
def api_run_vlm(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting VLM extraction...")
        run_vlm_extraction(cfg)
        logger.info("[API] VLM extraction finished.")

    if async_run:
        background_tasks.add_task(_job)
        return _response("vlm", status="started")
    _job()
    return _response("vlm")


@app.post("/api/steps/novel", response_model=StepResponse)
def api_run_novel(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting novelization...")
        run_novelization(cfg)
        logger.info("[API] Novelization finished.")

    if async_run:
        background_tasks.add_task(_job)
        return _response("novel", status="started")
    _job()
    return _response("novel")


@app.post("/api/steps/anchors", response_model=StepResponse)
def api_run_anchors(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting anchor extraction...")
        run_anchor_extraction(cfg)
        logger.info("[API] Anchor extraction finished.")

    if async_run:
        background_tasks.add_task(_job)
        return _response("anchors", status="started")
    _job()
    return _response("anchors")


@app.post("/api/steps/branches", response_model=StepResponse)
def api_run_branches(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting branch suggestion...")
        run_branching(cfg)
        logger.info("[API] Branch suggestion finished.")

    if async_run:
        background_tasks.add_task(_job)
        return _response("branches", status="started")
    _job()
    return _response("branches")


@app.post("/api/steps/characters", response_model=StepResponse)
def api_run_characters(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting character analysis...")
        run_character_analysis(cfg)
        logger.info("[API] Character analysis finished.")

    if async_run:
        background_tasks.add_task(_job)
        return _response("characters", status="started")
    _job()
    return _response("characters")


@app.post("/api/steps/scales", response_model=StepResponse)
def api_run_scales(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting scales computation...")
        run_scales(cfg)
        logger.info("[API] Scales computation finished.")

    if async_run:
        background_tasks.add_task(_job)
        return _response("scales", status="started")
    _job()
    return _response("scales")


@app.post("/api/steps/refine", response_model=StepResponse)
def api_run_refine(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Starting refinement + story index build...")
        run_refinement(cfg)
        logger.info("[API] Refinement finished.")

    if async_run:
        background_tasks.add_task(_job)
        return _response("refine", status="started")
    _job()
    return _response("refine")


@app.post("/api/steps/story-index", response_model=StepResponse)
def api_build_story_index(background_tasks: BackgroundTasks, async_run: bool = False):
    cfg = _load_cfg()

    def _job():
        logger.info("[API] Building story index...")
        run_story_index(cfg)
        logger.info("[API] Story index finished.")

    if async_run:
        background_tasks.add_task(_job)
        return _response("story-index", status="started")
    _job()
    return _response("story-index")


@app.post("/api/steps/continue-main", response_model=StepResponse)
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
        return _response("continue-main", status="started")
    _job()
    return _response("continue-main")


@app.post("/api/steps/branch-plan", response_model=StepResponse)
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
        return _response("branch-plan", status="started")
    _job()
    return _response("branch-plan")


@app.post("/api/steps/branch-generate", response_model=StepResponse)
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
        return _response("branch-generate", status="started")
    _job()
    return _response("branch-generate")


@app.post("/api/steps/branch-continue", response_model=StepResponse)
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
        return _response("branch-continue", status="started")
    _job()
    return _response("branch-continue")


@app.get("/api/logs/latest")
def api_logs_latest(limit: int = 200):
    try:
        from logging_config import LOG_PATH

        lines: List[str] = []
        if LOG_PATH.exists():
            content = LOG_PATH.read_text(encoding="utf-8").splitlines()
            lines = content[-limit:]
        return {"status": "ok", "step": "logs", "lines": lines}
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to read logs: %s", exc)
        return {"status": "error", "step": "logs", "lines": []}

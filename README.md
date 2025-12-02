# Manga Continuation Pipeline (FastAPI + React Dashboard)

This project is a full **manga → structured JSON → novel + new chapters** pipeline
built around xAI's Grok models and a 2M-token context window. It now ships with a
FastAPI wrapper and a React + Vite + Material UI dashboard so each pipeline step
can be triggered from a UI.

## Architecture

- **Python core (backend/pipeline_core.py + manga_pipeline/)** — segmentation,
  VLM summaries, refinement, novelization, anchors, branching, character bible,
  scales, and story continuation.
- **Story Index + Refinement** — summaries are aggregated into a global
  `data/story_index/story_index.json` map of arcs, intents, and chapter order,
  which is used to run a second-pass refinement on each chapter summary.
- **FastAPI API (backend/api.py)** — one endpoint per step with optional
  fire-and-forget execution (`async_run=true`).
- **React dashboard (frontend/)** — Vite + Material UI cards for each step,
  branch controls, and a simple log panel.
- **Root tooling** — a root `package.json` with `concurrently` to start the
  backend (uvicorn) and frontend (Vite) together.

## Directory Layout

```text
project-root/
  backend/
    pipeline_core.py    # CLI-compatible pipeline wrapper used by the API
    api.py              # FastAPI app exposing endpoints for each step
    requirements.txt    # backend dependencies
  frontend/
    index.html
    package.json
    vite.config.ts
    tsconfig*.json
    src/
      main.tsx
      App.tsx
      apiClient.ts
      components/
        PipelineDashboard.tsx
        StepCard.tsx
        LogsPanel.tsx
  manga_pipeline/       # Original modular pipeline implementation
  0_config/             # Configuration (e.g., config.yaml)
  package.json          # Root scripts (concurrently)
```

## Setup

1. **Python environment**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows
   pip install -r requirements.txt
   ```
   Add your xAI API key in `0_config/config.yaml` under `models.api_key` or set
   `XAI_API_KEY` in the environment.

2. **Node environment**
   ```bash
   # from repo root
   npm install  # installs concurrently at the root
   cd frontend && npm install
   ```

## Running the stack

From the repository root:

```bash
npm run dev
```

This starts uvicorn on **http://localhost:8000** and Vite on
**http://localhost:5173**. The dashboard cards call the API endpoints for each
pipeline step. Logs and artifacts still write to the paths configured in
`0_config/config.yaml`.

## CLI usage (optional)

The classic CLI remains available via `backend/pipeline_core.py`:

```bash
cd backend
python pipeline_core.py --step chapters|vlm|novel|refine|anchors|branches|branch_generate|characters|scales|continue|all \
  [--branch_id BRANCH] [--timeline_path PATH]
```

## Notes on prompts and models

- Prompts use system-style instructions and JSON-first outputs to align with
  xAI guidance.
- The pipeline uses rolling context and schema-focused prompts to maintain
  continuity across long stories.
- Future work can add a second-pass refinement endpoint/UI to reprocess all
  chapter summaries with global context.

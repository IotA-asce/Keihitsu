# Manga Continuation Pipeline (Grok + JSON Summaries)

This project is a full **manga → structured JSON → novel + new chapters** pipeline,
built around xAI's Grok models and a 2M-token context window.

It started from the Reddit discussion:

> *"Building a full manga continuation pipeline (Grok + JSON summaries → new chapters)"*

and has since evolved into a modular system that you can extend, debug, and later
hook into a UI.

---

## High-Level Flow

1. **Ingest / Understanding (VLM)**
   - Segment raw manga pages into chapters
   - For each chapter, a VLM (Grok Vision) produces a **structured JSON summary**:
     - `chapter_id`
     - `events[]`
     - `dialogues[]`
     - `visual_details { setting, atmosphere }`
     - `page_summaries[]` (panel-level narration)

2. **Second-Pass Refinement (Global Context)**
   - Once all chapters are summarized, a second pass refines each summary
     **with awareness of the entire story**.
   - This addresses the issue where early chapters were decoded
     “in the dark” before the model saw later reveals.

3. **Novelization (Prose)**
   - JSON summaries → light novel chapters (`ch_XXX.md`).
   - A rolling `story_so_far.txt` maintains continuity.
   - Full novel concatenated into `full_novel.md`.

4. **Story Analysis**
   - **Anchors** (`anchors.json`):
     - Key turning points with branching potential.
   - **Branch Suggestions** (`branches.json`):
     - For high-potential anchors, generate Behavioral / Bad End / Wildcard routes.
   - **Character Bible** (`characters.json`):
     - Main characters, roles, appearance, relationships, arcs.
   - **Scales** (`scales_by_chapter.json`):
     - Erotism / Romance / Action scores, genre/content flags.

5. **Continuation & Branch Timelines**
   - **Mainline JSON continuation**:
     - Uses only JSON summaries (no prose) to generate `ch_N+1.summary.json`.
     - Page-batched to avoid long-generation “dumbing down”.
   - **Branch timelines**:
     - Starting from a chosen `branch_id`, simulate a new chapter under
       that “what if”.
     - Optional `BranchConfig` lets you:
       - Introduce new characters
       - Force specific decisions (e.g. “MC never forgives rival”)

6. **Future UI-Friendly Design**
   - Each step is a separate module and CLI step.
   - You can later add:
     - A UI for selecting anchors and branches
     - Controls for tone, darkness, or pacing
     - Visual timeline of main and alternate routes

---

## Directory Layout

```text
manga-pipeline/
├── main.py                         # CLI entrypoint
├── manga_pipeline/
│   ├── core.py                     # config, paths, logging, shared utils
│   ├── schemas.py                  # Pydantic models + JSON schemas
│   ├── llm.py                      # TextLLMClient / VLMClient (xai-sdk)
│   ├── ingest.py                   # segmentation + VLM summaries
│   ├── refine_summaries.py         # second-pass refinement
│   ├── novelization.py             # prose chapters + rolling summary
│   ├── anchors.py                  # anchor extraction
│   ├── branches.py                 # branch suggestions + branch chapters
│   ├── characters.py               # character bible
│   ├── scales.py                   # content/genre scales
│   └── continuation.py             # mainline/alt JSON continuation
├── 0_config/
│   └── config.yaml                 # paths + model configuration
├── schemas_json/                   # optional JSON Schema dumps
└── README.md
```

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

pip install -U pip
pip install xai-sdk opencv-python numpy pyyaml regex tqdm pydantic
```

You also need to set your xAI API key **either** in:

* `0_config/config.yaml` under `models.api_key`, **or**
* Environment variable `XAI_API_KEY`.

---

## Configuration

Example `0_config/config.yaml`:

```yaml
paths:
  pages_dir: "1_pages"
  chapters_dir: "2_chapters"
  chapter_summaries_dir: "3_summaries"
  novel_dir: "4_novel"
  timeline_dir: "5_timeline"
  characters_dir: "6_characters"
  scales_dir: "7_scales"

models:
  api_key: "YOUR_XAI_API_KEY_HERE"
  text_model_id: "grok-4-1-fast"
  vlm_model_id: "grok-vision-beta"

scales:
  erotism_min: 0
  erotism_max: 5
  romance_min: 0
  romance_max: 5
  action_min: 0
  action_max: 5

continuation:
  target_pages: 18
```

---

## CLI Usage

The main entrypoint is:

```bash
python main.py --step <step-name> [--branch_id ...] [--timeline_path ...]
```

Available steps:

* `chapters` – Segment raw pages → per-chapter folders + `chapters_index.json`
* `vlm` – VLM summaries → `3_summaries/ch_XXX.summary.json`
* `refine` – Second-pass refinement → `ch_XXX.summary.refined.json`
* `novel` – Prose novelization → `4_novel/ch_XXX.md` + `full_novel.md`
* `anchors` – Anchor extraction → `5_timeline/ch_XXX.anchors.json` + `anchors.json`
* `branches` – Branch suggestions → `5_timeline/branches.json`
* `branch_generate` – First branch chapter for a chosen branch id
* `characters` – Character bible → `6_characters/characters.json`
* `scales` – Per-chapter content scales → `7_scales/`
* `continue` – Mainline continuation (or alternate timeline with `--timeline_path`)
* `all` – Run a full pass: `chapters → vlm → refine → novel → anchors → branches → characters → scales → continue`

Examples:

```bash
# Full pipeline
python main.py --step all

# Just run VLM extraction
python main.py --step vlm

# Refine summaries after you already have *.summary.json
python main.py --step refine

# Generate first branch chapter for a chosen branch id
python main.py --step branch_generate --branch_id ch_005_a001_b01

# Continue mainline story (JSON only)
python main.py --step continue
```

---

## Why Two-Pass Summaries?

While Grok has a 2M token context window, in practice:

* Very long generations degrade: the model starts compressing and “dumbing down” the output.
* Early chapters are interpreted without knowledge of later twists.

This pipeline handles that by:

1. **First pass**: smaller, local VLM batches per chapter
2. **Second pass** (`refine` step): a large-context Grok call that:

   * Sees the **whole story** as JSON
   * Corrects earlier misinterpretations
   * Harmonizes events and terminology across chapters

Novelization and continuation can then tap into these **refined** summaries, resulting in
new chapters that feel closer to the original author’s intent.

---

## Branching & Future UI

The branching system is designed to be UI-friendly:

* Every anchor event has:

  * `importance_score`
  * `branching_potential`
* High-potential anchors get 3 suggested routes:

  * **Behavioral** – character chooses differently
  * **Bad End** – failure route
  * **Wildcard** – external disruption
* A `BranchConfig` JSON lets you:

  * Introduce a new character in that timeline
  * Hard-code specific decisions / constraints

You can later expose this in a UI as:

* Anchor cards
* Toggle switches to turn on/off routes
* Forms to add a new character and mark them as “major” for this route

---

## JSON Schemas & Validation

All structured outputs go through **Pydantic models** (`schemas.py`).
You can optionally dump JSON Schemas via:

```python
from pathlib import Path
from manga_pipeline.schemas import dump_json_schemas

dump_json_schemas(Path("schemas_json"))
```

This gives you:

* `chapter_summary.schema.json`
* `anchor_list.schema.json`
* `branch_suggestions.schema.json`
* `character_bible.schema.json`
* `chapter_scales.schema.json`

Use these for:

* Validation in a UI
* Stronger enforcement of LLM outputs
* Interop with other tools / languages

---

## Known Limitations & Next Steps

* **Image → panel layout**: right now, the VLM only produces text summaries. You can later
  extend `VLMClient.describe_chapter` to emit panel bounding boxes if you want to regenerate
  pages visually.
* **Token budgeting**: with 2M context, you’re safe for most series, but throttling may kick
  in for extremely long runs. The pipeline already:

  * Uses batch generation
  * Truncates global contexts sensibly
* **UI integration**: the architecture is designed to plug into a web or desktop UI:

  * Chapters, anchors, branches, characters, and scales are all just JSON files.

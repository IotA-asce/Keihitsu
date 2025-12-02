# Keihitsu Architecture Overview

## Pipeline Steps
1. **Chapter segmentation** → splits pages into chapter folders.
2. **VLM extraction** → Grok Vision batches to produce JSON chapter summaries.
3. **Story index build** → `manga_pipeline/story_index.py` aggregates summaries into `data/story_index/story_index.json` capturing chapter order, intents, arcs, and themes.
4. **Summary refinement** → `manga_pipeline/refine_summaries.py` reruns summaries with global context to correct mistakes.
5. **Novelization** → converts summaries into prose chapters.
6. **Anchor extraction** → identifies pivotal events with `AnchorListSchema`, retrying on empty outputs.
7. **Branch suggestions** → proposes Behavioral / Bad End / Wildcard routes per anchor.
8. **Branch/mainline continuation** → builds new chapter JSON using rolling context.

## Schemas & Validation
Central schemas live in `manga_pipeline/schemas.py` and are reused across pipeline steps. `TextLLMClient.generate` can accept a schema to force JSON-only replies with validation/retry. A registry (`JSON_SCHEMA_REGISTRY`) exposes the common structures for dumping JSON schema files if needed.

## Logging
`backend/logging_config.py` configures a rotating log at `data/logs/keihitsu.log`. The API exposes `GET /api/logs/latest` for quick inspection in the dashboard.

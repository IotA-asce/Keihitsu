import json

import pytest

try:
    from manga_pipeline.core import extract_json_from_text
    from manga_pipeline.schemas import (
        AnchorListSchema,
        AnchorSchema,
        BranchOptionSchema,
        ChapterIndexEntry,
        ChapterScalesSchema,
        ChapterSummarySchema,
        StoryIndexSchema,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - guard for missing optional deps
    pytest.skip(f"Skipping schema tests because dependency missing: {exc}", allow_module_level=True)


def test_chapter_summary_coerces_page_summaries():
    data = {
        "chapter_id": "ch_001",
        "events": ["A"],
        "dialogues": ["Hello"],
        "visual_details": {"setting": "school", "atmosphere": "moody"},
        "page_summaries": ["first page"],
        "confidence_score": 0.8,
    }
    summary = ChapterSummarySchema.model_validate(data)
    assert summary.page_summaries[0].page_number == 1
    assert summary.page_summaries[0].text == "first page"


def test_anchor_and_branch_schemas_round_trip():
    anchor = AnchorSchema(
        anchor_id="ch_001_a01",
        chapter_id="ch_001",
        summary="Hero meets rival",
        characters=["Hero", "Rival"],
        cause="Assignment",
        immediate_effect="Tension",
        long_term_impact="Future conflict",
        importance_score=4,
        branching_potential=5,
    )
    branch = BranchOptionSchema(
        branch_id="b01",
        anchor_id=anchor.anchor_id,
        branch_type="Behavioral",
        what_if="Hero refuses",
        trigger_character="Hero",
        short_effect="Argument",
        long_effect="New alliance",
        tone="hopeful",
        new_characters=[{"name": "Rin"}],
        forced_decisions=["Hero apologizes"],
    )
    anchors = AnchorListSchema(anchors=[anchor])
    assert anchors.model_dump()["anchors"][0]["summary"] == "Hero meets rival"
    assert branch.model_dump()["tone"] == "hopeful"


def test_story_index_schema_validates():
    story_index = StoryIndexSchema(
        chapters=[
            ChapterIndexEntry(
                chapter_id="ch_001",
                chapter_number=1,
                title="Arrival",
                timeframe_label="day 1",
                primary_locations=["city"],
                primary_characters=["Hero"],
                summary="Hero arrives",
                chapter_intent="Introduce hero",
            )
        ],
        global_arcs=["Rivalry"],
        recurring_themes=["Hope"],
    )
    dumped = story_index.model_dump()
    assert dumped["chapters"][0]["chapter_intent"] == "Introduce hero"


def test_extract_json_from_text_with_code_fence():
    content = """
Response:
```json
{"value": 1, "text": "ok"}
```
Extra words
"""
    extracted = extract_json_from_text(content)
    loaded = json.loads(extracted)
    assert loaded["value"] == 1
    assert loaded["text"] == "ok"

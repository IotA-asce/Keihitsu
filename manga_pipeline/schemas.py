from __future__ import annotations

"""Centralized pydantic schemas for pipeline JSON structures."""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Type

from pydantic import BaseModel, Field, validator

from .core import ensure_dir


class PageSummary(BaseModel):
    page_number: int
    text: str


class VisualDetails(BaseModel):
    setting: str = ""
    atmosphere: str = ""


class ChapterSummarySchema(BaseModel):
    chapter_id: str
    events: List[str] = Field(default_factory=list)
    dialogues: List[str] = Field(default_factory=list)
    visual_details: VisualDetails = Field(default_factory=VisualDetails)
    page_summaries: List[PageSummary] = Field(default_factory=list)
    coverage_notes: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @validator("page_summaries", pre=True)
    def coerce_page_summaries(cls, v: Any) -> List[Dict[str, Any]]:
        if v is None:
            return []
        coerced: List[Dict[str, Any]] = []
        for idx, item in enumerate(v):
            if isinstance(item, str):
                coerced.append({"page_number": idx + 1, "text": item})
            else:
                coerced.append(item)
        return coerced


class AnchorSchema(BaseModel):
    anchor_id: str
    chapter_id: str
    summary: str
    characters: List[str]
    cause: str
    immediate_effect: str
    long_term_impact: str
    importance_score: int = Field(ge=1, le=5)
    branching_potential: int = Field(ge=1, le=5)


class AnchorListSchema(BaseModel):
    anchors: List[AnchorSchema] = Field(default_factory=list)


class BranchOptionSchema(BaseModel):
    branch_id: str
    anchor_id: str
    branch_type: Literal["Behavioral", "BadEnd", "Wildcard", "Custom"]
    what_if: str
    trigger_character: str
    short_effect: str
    long_effect: str
    tone: Optional[str] = None
    new_characters: List[Dict[str, Any]] = Field(default_factory=list)
    forced_decisions: List[str] = Field(default_factory=list)


class BranchSuggestionsByAnchor(BaseModel):
    branches_by_anchor: Dict[str, List[BranchOptionSchema]] = Field(
        default_factory=dict
    )


class BranchConfig(BaseModel):
    branch_id: str
    introduce_characters: List[Dict[str, Any]] = Field(default_factory=list)
    force_decisions: List[Dict[str, str]] = Field(default_factory=list)


class CharacterSchema(BaseModel):
    character_id: str
    names: List[str]
    role: str
    appearance: str = ""
    personality: str = ""
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    arc_summary: List[str] = Field(default_factory=list)


class CharacterBible(BaseModel):
    characters: List[CharacterSchema] = Field(default_factory=list)


class ChapterScalesSchema(BaseModel):
    chapter_id: str
    erotism_score: int = 0
    romance_score: int = 0
    action_score: int = 0
    genre_labels: List[str] = Field(default_factory=list)
    content_labels: List[str] = Field(default_factory=list)


class ChapterIndexEntry(BaseModel):
    chapter_id: str
    chapter_number: int
    title: Optional[str] = None
    timeframe_label: Optional[str] = None
    primary_locations: List[str] = Field(default_factory=list)
    primary_characters: List[str] = Field(default_factory=list)
    summary: str
    chapter_intent: str


class StoryIndexSchema(BaseModel):
    chapters: List[ChapterIndexEntry]
    global_arcs: List[str] = Field(default_factory=list)
    recurring_themes: List[str] = Field(default_factory=list)


class MainlineChapterPlanSchema(BaseModel):
    chapter_id: str
    objectives: List[str] = Field(default_factory=list)
    beats: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    timeframe_hint: Optional[str] = None
    global_arcs: List[str] = Field(default_factory=list)


class BranchChapterPlanSchema(BaseModel):
    branch_id: str
    chapter_plan: MainlineChapterPlanSchema
    divergence_notes: Optional[str] = None


JSON_SCHEMA_REGISTRY: Dict[str, Type[BaseModel]] = {
    "chapter_summary": ChapterSummarySchema,
    "anchor": AnchorSchema,
    "anchor_list": AnchorListSchema,
    "branch_option": BranchOptionSchema,
    "branch_suggestions": BranchSuggestionsByAnchor,
    "character": CharacterSchema,
    "character_bible": CharacterBible,
    "chapter_scales": ChapterScalesSchema,
    "story_index": StoryIndexSchema,
    "mainline_plan": MainlineChapterPlanSchema,
    "branch_plan": BranchChapterPlanSchema,
}


# Backwards-compatibility aliases used across the codebase
ChapterSummary = ChapterSummarySchema
AnchorEvent = AnchorSchema
AnchorList = AnchorListSchema
BranchSuggestion = BranchOptionSchema
ChapterScales = ChapterScalesSchema


def dump_json_schemas(output_dir: Path) -> None:
    ensure_dir(output_dir)

    for key, model in JSON_SCHEMA_REGISTRY.items():
        schema_path = output_dir / f"{key}.schema.json"
        schema = model.model_json_schema()
        with schema_path.open("w", encoding="utf-8") as f:
            import json

            json.dump(schema, f, indent=2, ensure_ascii=False)

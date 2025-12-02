from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .core import ensure_dir


class ChapterSummary(BaseModel):
    chapter_id: str
    events: List[str] = Field(default_factory=list)
    dialogues: List[str] = Field(default_factory=list)
    visual_details: Dict[str, str] = Field(
        default_factory=lambda: {"setting": "", "atmosphere": ""}
    )
    page_summaries: List[str] = Field(default_factory=list)

    @validator("visual_details", pre=True, always=True)
    def ensure_visual_fields(cls, v: Any) -> Dict[str, str]:
        v = v or {}
        return {
            "setting": v.get("setting", ""),
            "atmosphere": v.get("atmosphere", ""),
        }


class AnchorEvent(BaseModel):
    anchor_id: str
    chapter_id: str
    summary: str
    characters: List[str] = Field(default_factory=list)
    cause: str = ""
    immediate_effect: str = ""
    long_term_impact: str = ""
    importance_score: int = 3
    branching_potential: int = 3


class AnchorList(BaseModel):
    anchors: List[AnchorEvent] = Field(default_factory=list)


class BranchSuggestion(BaseModel):
    branch_id: str
    anchor_id: str
    branch_type: str
    what_if: str
    trigger_character: str
    short_effect: str
    long_effect: str


class BranchSuggestionsByAnchor(BaseModel):
    branches_by_anchor: Dict[str, List[BranchSuggestion]] = Field(
        default_factory=dict
    )


class BranchConfig(BaseModel):
    branch_id: str
    introduce_characters: List[Dict[str, Any]] = Field(default_factory=list)
    force_decisions: List[Dict[str, str]] = Field(default_factory=list)


class CharacterProfile(BaseModel):
    character_id: str
    names: List[str]
    role: str
    appearance: str = ""
    personality: str = ""
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    arc_summary: List[str] = Field(default_factory=list)


class CharacterBible(BaseModel):
    characters: List[CharacterProfile] = Field(default_factory=list)


class ChapterScales(BaseModel):
    chapter_id: str
    erotism_score: int = 0
    romance_score: int = 0
    action_score: int = 0
    genre_labels: List[str] = Field(default_factory=list)
    content_labels: List[str] = Field(default_factory=list)


def dump_json_schemas(output_dir: Path) -> None:
    ensure_dir(output_dir)

    for model, name in [
        (ChapterSummary, "chapter_summary"),
        (AnchorList, "anchor_list"),
        (BranchSuggestionsByAnchor, "branch_suggestions"),
        (CharacterBible, "character_bible"),
        (ChapterScales, "chapter_scales"),
    ]:
        schema_path = output_dir / f"{name}.schema.json"
        schema = model.model_json_schema()
        with schema_path.open("w", encoding="utf-8") as f:
            import json

            json.dump(schema, f, indent=2, ensure_ascii=False)

import json
import logging
from pathlib import Path
from typing import Any, Dict

from .core import PROJECT_ROOT, ensure_dir, extract_json_from_text, save_json_safe
from .llm import TextLLMClient
from .schemas import CharacterBible

logger = logging.getLogger(__name__)


def _build_character_prompt(full_story_text: str) -> str:
    prompt = f"""
You are a character analyst.

Given the FULL STORY TEXT below, identify the main characters and produce
a CHARACTER BIBLE.

For each character, include:

- "character_id": short id like "c0", "c1", ...
- "names": list of names / aliases
- "role": short description of their role in the story
- "appearance": textual description (hair, clothing, distinctive features)
- "personality": short description
- "relationships": list of objects with:
    - "to": character name or id
    - "type": e.g. "friend", "rival", "romantic interest"
    - "arc": how the relationship changes across the story
- "arc_summary": bullet-like list of major beats in their personal arc

OUTPUT:
- ONE JSON object: { "characters": [ ... ] }
- No commentary.

FULL STORY TEXT:
"""
{full_story_text}
"""
"""
    return prompt.strip()


def run_character_analysis(cfg: Dict[str, Any]) -> None:
    paths_cfg = cfg["paths"]
    models_cfg = cfg["models"]

    novel_dir = PROJECT_ROOT / paths_cfg["novel_dir"]
    characters_dir = ensure_dir(PROJECT_ROOT / paths_cfg["characters_dir"])

    full_path = novel_dir / "full_novel.md"
    if not full_path.exists():
        raise RuntimeError("full_novel.md not found. Run step 'novel' first.")

    full_story_text = full_path.read_text(encoding="utf-8")[-200000:]

    text_client = TextLLMClient(
        model_id=models_cfg["text_model_id"],
        api_key=models_cfg.get("api_key"),
    )

    logger.info("[characters] Building character bible...")
    prompt = _build_character_prompt(full_story_text)
    raw = text_client.generate(prompt, temperature=0.4)
    json_str = extract_json_from_text(raw)

    try:
        data = json.loads(json_str)
        bible = CharacterBible.model_validate(data)
    except Exception as e:  # noqa: BLE001
        logger.error("[characters] Failed to parse/validate character bible: %s", e)
        bible = CharacterBible(characters=[])

    global_path = characters_dir / "characters.json"
    save_json_safe(global_path, bible.model_dump())

    for ch in bible.characters:
        cid = ch.character_id or "unknown"
        cpath = characters_dir / f"{cid}.json"
        save_json_safe(cpath, ch.model_dump())

    logger.info("[characters] Wrote character bible → %s", global_path)

import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from xai_sdk import Client
from xai_sdk.chat import image, system, user

from pydantic import BaseModel, ValidationError

from .core import extract_json_from_text

logger = logging.getLogger(__name__)


class TextLLMClient:
    """Wrapper around xAI Grok for text-only generation using xai-sdk."""

    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        timeout: int = 3600,
        system_prompt: Optional[str] = None,
    ):
        if api_key is None:
            logger.info("TextLLMClient: using XAI_API_KEY from environment")
        self.model_id = model_id
        self.client = Client(api_key=api_key, timeout=timeout)
        self.system_prompt = system_prompt or (
            "You are a meticulous, structured assistant for a manga-to-novel "
            "pipeline. Always follow the requested format exactly."
        )

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 2048,
        temperature: float = 0.7,
        force_json: bool = False,
        schema: Optional[Type[BaseModel]] = None,
    ) -> str:
        if schema is not None:
            prompt = (
                f"{prompt}\n\n"
                "You MUST respond with ONLY a single valid JSON object. Use exactly the "
                "fields from this schema and no others: "
                f"{list(schema.model_fields.keys())}. Do not include commentary or code fences."
            )
        elif force_json:
            prompt = (
                f"{prompt}\n\n"
                "You MUST respond with ONLY a single valid JSON object. "
                "Do not include explanation, commentary, or markdown fences."
            )

        attempts = 3 if schema is not None else 1
        last_error: Optional[str] = None
        response_text = ""

        for attempt in range(1, attempts + 1):
            chat = self.client.chat.create(model=self.model_id)
            chat.append(system(self.system_prompt))
            chat.append(user(prompt))

            logger.debug(
                "TextLLMClient.generate: sending prompt (len=%d chars, attempt %d)",
                len(prompt),
                attempt,
            )

            resp = chat.sample(temperature=temperature)
            response_text = (resp.content or "").strip()
            logger.debug(
                "TextLLMClient.generate: received response (len=%d chars)",
                len(response_text),
            )

            if schema is None:
                return response_text

            json_payload = extract_json_from_text(response_text)
            try:
                schema.model_validate_json(json_payload)
                return json_payload
            except ValidationError as exc:
                last_error = str(exc)
                logger.warning(
                    "TextLLMClient.generate: validation failed attempt %d/%d: %s",
                    attempt,
                    attempts,
                    exc,
                )
                corrected_prompt = (
                    "The previous JSON was invalid for the expected schema. "
                    "Please return corrected JSON only, no commentary.\n\n"
                    f"Invalid JSON was:\n{json_payload}\n\n"
                    f"Validation errors:\n{exc}"
                )
                prompt = corrected_prompt

        logger.error("TextLLMClient.generate: failed to validate JSON after retries: %s", last_error)
        if schema is not None:
            try:
                return schema().model_dump_json()
            except Exception:  # noqa: BLE001
                return "{}"
        return response_text


class VLMClient:
    """Wrapper for visual-language capabilities via xai-sdk Client."""

    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        timeout: int = 3600,
    ):
        self.model_id = model_id
        self.client = Client(api_key=api_key, timeout=timeout)

    @staticmethod
    def encode_image(image_path: Path) -> str:
        with image_path.open("rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def is_title_page(self, image_path: Path) -> bool:
        logger.debug("VLMClient.is_title_page: checking %s", image_path)
        encoded = self.encode_image(image_path)
        prompt = (
            "Does this manga page contain a clear Chapter Title or large text "
            "indicating the start of a new chapter number/title? "
            "Answer ONLY 'YES' or 'NO'."
        )

        chat = self.client.chat.create(model=self.model_id)
        chat.append(
            user(
                prompt,
                image(
                    image_url=f"data:image/jpeg;base64,{encoded}",
                    detail="low",
                ),
            )
        )

        resp = chat.sample()
        content = (resp.content or "").strip().upper()
        logger.debug("VLMClient.is_title_page: model replied: %r", content)
        return "YES" in content

    def describe_chapter(self, chapter_id: str, image_paths: List[Path]) -> Dict[str, Any]:
        from tqdm import tqdm

        BATCH_SIZE = 10
        total_pages = len(image_paths)

        logger.info(
            "VLMClient.describe_chapter: chapter=%s, pages=%d", chapter_id, total_pages
        )

        aggregated: Dict[str, Any] = {
            "chapter_id": chapter_id,
            "events": [],
            "dialogues": [],
            "visual_details": {"setting": "", "atmosphere": ""},
            "page_summaries": [],
        }

        story_so_far = ""

        for batch_start in tqdm(
            range(0, total_pages, BATCH_SIZE),
            desc=f"VLM {chapter_id}",
            unit="batch",
        ):
            batch_paths = image_paths[batch_start : batch_start + BATCH_SIZE]
            batch_page_numbers = list(
                range(batch_start + 1, batch_start + 1 + len(batch_paths))
            )

            imgs_b64 = [self.encode_image(p) for p in batch_paths]

            story_context = (
                story_so_far
                if story_so_far
                else "This is the beginning of the chapter; no prior pages have been summarized yet."
            )

            prompt = f"""
You are an expert manga analyst. We are analyzing chapter {chapter_id} in multiple batches
to respect context limits. Reading direction is right to left, top to down.

STORY SO FAR (earlier pages of this chapter):
{story_context}

Now you will see ONLY pages {batch_page_numbers[0]}–{batch_page_numbers[-1]} out of {total_pages}.
Focus on these pages while keeping the STORY SO FAR in mind to maintain continuity.

Output a JSON object with these exact fields:
- "chapter_id": "{chapter_id}"
- "events": [list of key plot events occurring in THESE pages only]
- "dialogues": [list of key dialogue summaries from THESE pages only]
- "visual_details": {{ "setting": "...", "atmosphere": "..." }}
- "page_summaries": [an elaborate panel-by-panel narration of EACH page in this batch, in order.
                     Make sure the list length equals {len(batch_paths)} and that each entry clearly
                     mentions the absolute page number from this set: {batch_page_numbers}]

Return ONLY valid JSON.
""".strip()

            chat = self.client.chat.create(model=self.model_id)
            image_contents = [
                image(
                    image_url=f"data:image/jpeg;base64,{img_b64}",
                    detail="high",
                )
                for img_b64 in imgs_b64
            ]
            chat.append(user(prompt, *image_contents))

            logger.info(
                "VLMClient.describe_chapter: %s pages %d-%d",
                chapter_id,
                batch_page_numbers[0],
                batch_page_numbers[-1],
            )

            response = chat.sample()
            raw = response.content or ""
            json_str = extract_json_from_text(raw)

            try:
                batch_result: Dict[str, Any] = __import__("json").loads(json_str)
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "VLMClient.describe_chapter: JSON parse failed for %s pages %s: %s",
                    chapter_id,
                    batch_page_numbers,
                    e,
                )
                batch_result = {
                    "events": [],
                    "dialogues": [],
                    "visual_details": {},
                    "page_summaries": [],
                }

            batch_events = batch_result.get("events", []) or []
            batch_dialogues = batch_result.get("dialogues", []) or []
            batch_visual_details = batch_result.get("visual_details", {}) or {}
            batch_page_summaries = batch_result.get("page_summaries", []) or []

            aggregated["events"].extend(batch_events)
            aggregated["dialogues"].extend(batch_dialogues)
            aggregated["page_summaries"].extend(batch_page_summaries)

            for key in ("setting", "atmosphere"):
                val = batch_visual_details.get(key)
                if not val:
                    continue
                existing = aggregated["visual_details"].get(key, "")
                if not existing:
                    aggregated["visual_details"][key] = val
                elif val not in existing:
                    aggregated["visual_details"][key] = existing + " " + val

            events_text = ", ".join(aggregated["events"])[:2000]
            dialogues_text = ", ".join(aggregated["dialogues"])[:2000]
            story_so_far = (
                f"Key events so far in chapter {chapter_id}: {events_text}\n"
                f"Key dialogues so far: {dialogues_text}"
            )

        return aggregated

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from models import SceneObservation, WorldTurnDirector

load_dotenv()

BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
APP_REFERER = os.getenv("APP_REFERER", "http://localhost:3000")
APP_TITLE = os.getenv("APP_TITLE", "AI Time-Travel Explorer")
IMAGE_MODEL = os.getenv("OPENROUTER_IMAGE_MODEL", "openai/gpt-5.4-image-2")
WORLD_MODEL = os.getenv("WORLD_MODEL", os.getenv("STORY_MODEL", "x-ai/grok-3-mini"))
SCENE_OBSERVER_MODEL = os.getenv("SCENE_OBSERVER_MODEL", WORLD_MODEL)
SEEDANCE_MODEL = os.getenv("OPENROUTER_SEEDANCE_MODEL", "bytedance/seedance-2.0")


class OpenRouterError(RuntimeError):
    pass


def _format_http_error(exc: httpx.HTTPStatusError) -> str:
    response_text = ""
    try:
        response_text = exc.response.text
    except Exception:  # noqa: BLE001
        response_text = ""
    base = f"{exc}"
    return f"{base} | body={response_text}" if response_text else base


async def _post(endpoint: str, payload: dict[str, Any], timeout: float = 180.0) -> dict[str, Any]:
    if not OPENROUTER_API_KEY:
        raise OpenRouterError("OPENROUTER_API_KEY is missing")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": APP_REFERER,
        "X-Title": APP_TITLE,
    }

    attempts = 3
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{BASE_URL}{endpoint}", headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            last_exc = OpenRouterError(_format_http_error(exc))
            if i < attempts - 1 and exc.response.status_code >= 500:
                await asyncio.sleep(1.0 * (i + 1))
                continue
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if i < attempts - 1:
                await asyncio.sleep(1.0 * (i + 1))

    raise OpenRouterError(f"OpenRouter request failed: {last_exc}") from last_exc


async def _get(endpoint: str, timeout: float = 120.0) -> dict[str, Any]:
    if not OPENROUTER_API_KEY:
        raise OpenRouterError("OPENROUTER_API_KEY is missing")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": APP_REFERER,
        "X-Title": APP_TITLE,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(f"{BASE_URL}{endpoint}", headers=headers)
        resp.raise_for_status()
        return resp.json()


async def generate_initial_keyframe(prompt: str) -> str:
    payload = {
        "model": IMAGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image"],
        "image_config": {"aspect_ratio": "16:9", "image_size": "2K"},
        "stream": False,
    }
    result = await _post("/chat/completions", payload, timeout=180.0)

    model_choices = result.get("choices") or []
    if not model_choices:
        raise OpenRouterError(f"No choices returned for image generation: {result}")

    message = model_choices[0].get("message", {})
    images = message.get("images") or []
    if not images:
        raise OpenRouterError(f"No images returned: {result}")

    image_obj = images[0]
    image_url = (
        image_obj.get("image_url", {}).get("url")
        or image_obj.get("imageUrl", {}).get("url")
        or image_obj.get("url")
    )
    if not image_url:
        raise OpenRouterError(f"Missing image URL in response: {result}")
    return str(image_url)


def _normalize_string_list(raw: Any, *, max_items: int) -> list[str]:
    if not isinstance(raw, list):
        return []
    values: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            values.append(text)
        if len(values) >= max_items:
            break
    return values


async def _request_json_completion(*, model: str, system_prompt: str, user_content: Any) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
    }
    result = await _post("/chat/completions", payload, timeout=120.0)

    model_choices = result.get("choices") or []
    if not model_choices:
        raise OpenRouterError(f"No choices returned: {result}")

    content = model_choices[0].get("message", {}).get("content", "")
    if not content:
        raise OpenRouterError(f"No content returned: {result}")

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"Invalid JSON content from model: {content}") from exc


async def generate_world_turn(system_prompt: str, user_prompt: str) -> WorldTurnDirector:
    parsed = await _request_json_completion(
        model=WORLD_MODEL,
        system_prompt=system_prompt,
        user_content=user_prompt,
    )

    narrator_text = str(parsed.get("narrator_text", "")).strip()
    action_result = str(parsed.get("action_result", "")).strip()
    video_prompt = str(parsed.get("video_prompt", "")).strip()
    updated_world_summary = str(parsed.get("updated_world_summary", "")).strip()

    if not narrator_text:
        raise OpenRouterError(f"narrator_text missing in model response: {parsed}")
    if not action_result:
        action_result = narrator_text
    if not video_prompt:
        raise OpenRouterError(f"video_prompt missing in model response: {parsed}")
    if not updated_world_summary:
        updated_world_summary = narrator_text

    return WorldTurnDirector(
        narrator_text=narrator_text,
        action_result=action_result,
        video_prompt=video_prompt,
        updated_world_summary=updated_world_summary,
        inventory_delta=_normalize_string_list(parsed.get("inventory_delta"), max_items=8),
        memory_tags=_normalize_string_list(parsed.get("memory_tags"), max_items=16),
        safety_mode=str(parsed.get("safety_mode", "normal")).strip() or "normal",
        should_generate_video=bool(parsed.get("should_generate_video", True)),
    )


async def generate_scene_observation(system_prompt: str, image_url: str) -> SceneObservation:
    parsed = await _request_json_completion(
        model=SCENE_OBSERVER_MODEL,
        system_prompt=system_prompt,
        user_content=[
            {"type": "text", "text": "Observe this current scene frame."},
            {"type": "image_url", "image_url": {"url": image_url}},
        ],
    )

    location = str(parsed.get("location", "")).strip() or "Unknown location"
    mood = str(parsed.get("mood", "")).strip() or "unclear"
    lighting = str(parsed.get("lighting", "")).strip() or "natural"
    player_perspective = str(parsed.get("player_perspective", "")).strip() or "first-person"
    raw_caption = str(parsed.get("raw_caption", "")).strip() or "The scene remains still for a moment."

    return SceneObservation(
        location=location,
        visible_characters=_normalize_string_list(parsed.get("visible_characters"), max_items=12),
        visible_objects=_normalize_string_list(parsed.get("visible_objects"), max_items=20),
        mood=mood,
        lighting=lighting,
        player_perspective=player_perspective,
        possible_affordances=_normalize_string_list(parsed.get("possible_affordances"), max_items=12),
        dangers=_normalize_string_list(parsed.get("dangers"), max_items=12),
        raw_caption=raw_caption,
    )


async def request_video_generation(
    prompt: str,
    first_frame_url: str,
    last_frame_url: str | None = None,
    duration: int = 8,
    generate_audio: bool = False,
) -> str:
    frame_images = [
        {"type": "image_url", "image_url": {"url": first_frame_url}, "frame_type": "first_frame"},
    ]
    if last_frame_url:
        frame_images.append(
            {"type": "image_url", "image_url": {"url": last_frame_url}, "frame_type": "last_frame"}
        )

    payload = {
        "model": SEEDANCE_MODEL,
        "prompt": prompt,
        "frame_images": frame_images,
        "duration": duration,
        "resolution": "1080p",
        "generate_audio": generate_audio,
    }

    result = await _post("/videos", payload, timeout=120.0)
    task_id = result.get("id") or result.get("task_id")
    if not task_id:
        raise OpenRouterError(f"Video request missing task id: {result}")
    return str(task_id)


async def poll_video(task_id: str, timeout_seconds: int = 180) -> dict[str, Any]:
    elapsed = 0
    interval = 3
    while elapsed < timeout_seconds:
        status = await _get(f"/videos/{task_id}", timeout=60.0)

        video_url = (
            status.get("video_url")
            or status.get("output", {}).get("video_url")
            or status.get("data", {}).get("video_url")
            or ((status.get("unsigned_urls") or [None])[0])
        )
        state = str(status.get("status", "")).lower()

        if video_url:
            return {"done": True, "video_url": video_url, "raw": status}
        if state in {"failed", "error", "cancelled"}:
            raise OpenRouterError(f"Video generation failed: {status}")

        await asyncio.sleep(interval)
        elapsed += interval

    return {"done": False, "video_url": None, "raw": {"status": "timeout", "task_id": task_id}}

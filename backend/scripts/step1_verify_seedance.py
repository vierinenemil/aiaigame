from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from prompts import INITIAL_KEYFRAME_PROMPT
from services.openrouter import (
    _get,
    OpenRouterError,
    generate_initial_keyframe,
    request_video_generation,
)
from services.storage import load_starter_frame_data_url


def build_prompt(custom_action: str) -> str:
    return (
        "Seamless cinematic continuation. Exact first frame and last frame MUST match the provided "
        "reference images perfectly - no changes to lighting, character, or environment. "
        f"Player just did: '{custom_action}'. "
        "Current story: You are in an ancient library time-portal hub. "
        "Realistic physics, natural camera movement, same style, 8 seconds, native synchronized audio "
        "with ambient sounds, effects, and subtle music."
    )


async def main(action: str) -> None:
    try:
        print("Resolving starter frame...", flush=True)
        frame_url = load_starter_frame_data_url()
        if frame_url:
            print("Using preset starter image from local assets.", flush=True)
        else:
            print("No preset starter image found, generating initial keyframe...", flush=True)
            frame_url = await generate_initial_keyframe(INITIAL_KEYFRAME_PROMPT)
        print(f"FRAME_URL: {frame_url[:120]}...", flush=True)

        print("Submitting Seedance video job...", flush=True)
        task_id = await request_video_generation(
            seedance_prompt=build_prompt(action),
            first_frame_url=frame_url,
            last_frame_url=frame_url,
            duration=8,
        )
        print(f"TASK_ID: {task_id}", flush=True)

        elapsed = 0
        timeout_seconds = 600
        interval = 5
        while elapsed < timeout_seconds:
            status = await _get(f"/videos/{task_id}", timeout=60.0)
            state = str(status.get("status", "")).lower()
            unsigned = status.get("unsigned_urls") or []
            video_url = (
                status.get("video_url")
                or status.get("output", {}).get("video_url")
                or status.get("data", {}).get("video_url")
                or (unsigned[0] if unsigned else None)
            )
            print(f"POLL {elapsed:>3}s status={state or 'unknown'}", flush=True)
            if video_url:
                print("VIDEO_URL:", video_url, flush=True)
                return
            if state in {"failed", "error", "cancelled"}:
                raise RuntimeError(f"Video generation failed: {status}")
            await asyncio.sleep(interval)
            elapsed += interval

        raise RuntimeError(f"Video generation timed out after {timeout_seconds}s")
    except OpenRouterError as exc:
        raise RuntimeError(f"OpenRouter error: {exc}") from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 1 Seedance verification script")
    parser.add_argument("--action", default="step through the portal and look around")
    args = parser.parse_args()
    asyncio.run(main(args.action))

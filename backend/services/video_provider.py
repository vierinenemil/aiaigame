import os
from typing import Any

from services.openrouter import OpenRouterError, poll_video, request_video_generation
from services.video_config import VideoConfig


class VideoGenerationError(Exception):
    pass


def clean_prompt(prompt: str) -> str:
    return " ".join(prompt.strip().split())[:900]


async def generate_video(prompt: str, config: VideoConfig, first_frame_url: str | None = None) -> str:
    provider = config.provider.lower()

    if provider == "replicate_wan_i2v_fast":
        if not first_frame_url:
            raise VideoGenerationError("replicate_wan_i2v_fast requires first_frame_url")
        return await generate_replicate_wan_i2v_fast(prompt, config, first_frame_url)

    if provider == "replicate_wan_fast":
        return await generate_replicate_wan_fast(prompt, config)

    if provider == "fal_wan_fast":
        return await generate_fal_wan_fast(prompt, config)

    if provider == "fal_ltx_fast":
        return await generate_fal_ltx_fast(prompt, config)

    if provider == "openrouter_seedance_i2v":
        return await generate_openrouter_seedance_i2v(prompt, config, first_frame_url)

    raise VideoGenerationError(f"Unsupported video provider: {provider}")


def _wan_resolution(width: int, height: int) -> str:
    if width * height <= 832 * 480:
        return "480p"
    return "720p"


def _wan_aspect_ratio(width: int, height: int) -> str:
    if height <= 0:
        return "16:9"
    ratio = width / height
    if abs(ratio - (16 / 9)) < 0.1:
        return "16:9"
    if abs(ratio - (9 / 16)) < 0.1:
        return "9:16"
    return "1:1"


async def generate_replicate_wan_i2v_fast(prompt: str, config: VideoConfig, first_frame_url: str) -> str:
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise VideoGenerationError("Missing REPLICATE_API_TOKEN")

    import replicate

    client = replicate.Client(api_token=token)
    num_frames = max(81, int(config.seconds * config.fps) + 1)

    try:
        output = await client.async_run(
            "wan-video/wan-2.2-i2v-fast",
            input={
                "image": first_frame_url,
                "prompt": clean_prompt(prompt),
                "num_frames": num_frames,
                "resolution": _wan_resolution(config.width, config.height),
                "aspect_ratio": _wan_aspect_ratio(config.width, config.height),
                "frames_per_second": config.fps,
                "go_fast": True,
                "sample_shift": 12,
            },
        )
    except Exception as exc:
        raise VideoGenerationError(f"Replicate Wan I2V failed: {exc}") from exc

    return extract_video_url(output)


async def generate_replicate_wan_fast(prompt: str, config: VideoConfig) -> str:
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise VideoGenerationError("Missing REPLICATE_API_TOKEN")

    import replicate

    client = replicate.Client(api_token=token)

    try:
        output = await client.async_run(
            "wan-video/wan-2.2-5b-fast",
            input={
                "prompt": clean_prompt(prompt),
                "duration": config.seconds,
                "fps": config.fps,
                "width": config.width,
                "height": config.height,
            },
        )
    except Exception as exc:
        raise VideoGenerationError(f"Replicate Wan failed: {exc}") from exc

    return extract_video_url(output)


async def generate_fal_wan_fast(prompt: str, config: VideoConfig) -> str:
    if not os.getenv("FAL_KEY"):
        raise VideoGenerationError("Missing FAL_KEY")

    import fal_client

    try:
        result = await fal_client.run_async(
            "fal-ai/wan/v2.2-5b/text-to-video",
            arguments={
                "prompt": clean_prompt(prompt),
            },
        )
    except Exception as exc:
        raise VideoGenerationError(f"fal Wan failed: {exc}") from exc

    return extract_video_url(result)


async def generate_fal_ltx_fast(prompt: str, config: VideoConfig) -> str:
    if not os.getenv("FAL_KEY"):
        raise VideoGenerationError("Missing FAL_KEY")

    import fal_client

    try:
        result = await fal_client.run_async(
            "fal-ai/ltx-2/text-to-video/fast",
            arguments={
                "prompt": clean_prompt(prompt),
                "duration": config.seconds,
                "width": config.width,
                "height": config.height,
            },
        )
    except Exception as exc:
        raise VideoGenerationError(f"fal LTX failed: {exc}") from exc

    return extract_video_url(result)


async def generate_openrouter_seedance_i2v(prompt: str, config: VideoConfig, first_frame_url: str | None) -> str:
    if not first_frame_url:
        raise VideoGenerationError("Seedance i2v requires first_frame_url")

    try:
        task_id = await request_video_generation(
            prompt=clean_prompt(prompt),
            first_frame_url=first_frame_url,
            duration=config.seconds,
            generate_audio=config.audio,
        )
        result = await poll_video(task_id, timeout_seconds=180)
    except OpenRouterError as exc:
        raise VideoGenerationError(f"OpenRouter Seedance failed: {exc}") from exc

    video_url = result.get("video_url")
    if not video_url:
        raise VideoGenerationError("OpenRouter Seedance did not return a video URL")
    return str(video_url)


def extract_video_url(output: Any) -> str:
    url_attr = getattr(output, "url", None)
    if isinstance(url_attr, str) and url_attr.startswith(("http://", "https://")):
        return url_attr

    if isinstance(output, str):
        return output

    if output is not None:
        as_text = str(output).strip()
        if as_text.startswith(("http://", "https://")):
            return as_text

    if isinstance(output, list) and output:
        return extract_video_url(output[0])

    if isinstance(output, dict):
        for key in ["video_url", "url", "output"]:
            value = output.get(key)
            if value:
                return extract_video_url(value)

        video = output.get("video")
        if isinstance(video, dict):
            for key in ["url", "video_url"]:
                if video.get(key):
                    return video[key]

    raise VideoGenerationError(f"Could not extract video URL from output: {output}")

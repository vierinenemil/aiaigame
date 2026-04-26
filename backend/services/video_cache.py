import hashlib
import json
from pathlib import Path


def video_cache_key(
    prompt: str,
    provider: str,
    width: int,
    height: int,
    seconds: int,
    fps: int,
    source_image_hash: str | None = None,
) -> str:
    raw = json.dumps(
        {
            "prompt": prompt,
            "provider": provider,
            "width": width,
            "height": height,
            "seconds": seconds,
            "fps": fps,
            "source_image_hash": source_image_hash or "",
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def frame_source_hash(source: str | None) -> str:
    if not source:
        return ""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def get_cached_video(cache_dir: str, key: str) -> str | None:
    path = Path(cache_dir) / f"{key}.json"
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
        return data.get("video_url")
    except Exception:
        return None


def set_cached_video(cache_dir: str, key: str, video_url: str) -> None:
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)

    (path / f"{key}.json").write_text(json.dumps({"video_url": video_url}, indent=2))

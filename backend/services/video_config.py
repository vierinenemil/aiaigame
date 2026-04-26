import os
from dataclasses import dataclass


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class VideoConfig:
    enabled: bool
    provider: str
    width: int
    height: int
    seconds: int
    fps: int
    idle_loop_seconds: int
    audio: bool
    major_moments_only: bool
    every_n_turns: int
    max_per_session: int
    max_session_spend_usd: float
    cache_dir: str


def get_video_config() -> VideoConfig:
    return VideoConfig(
        enabled=env_bool("ENABLE_VIDEO_GENERATION", False),
        provider=os.getenv("VIDEO_PROVIDER", "replicate_wan_fast").strip(),
        width=env_int("VIDEO_WIDTH", 832),
        height=env_int("VIDEO_HEIGHT", 480),
        seconds=env_int("VIDEO_SECONDS", 5),
        fps=env_int("VIDEO_FPS", 16),
        idle_loop_seconds=max(1, env_int("IDLE_LOOP_SECONDS", 1)),
        audio=env_bool("VIDEO_AUDIO", False),
        major_moments_only=env_bool("VIDEO_MAJOR_MOMENTS_ONLY", True),
        every_n_turns=max(1, env_int("VIDEO_EVERY_N_TURNS", 4)),
        max_per_session=max(0, env_int("VIDEO_MAX_PER_SESSION", 3)),
        max_session_spend_usd=max(0.0, env_float("VIDEO_MAX_SESSION_SPEND_USD", 0.30)),
        cache_dir=os.getenv("VIDEO_CACHE_DIR", ".cache/videos"),
    )

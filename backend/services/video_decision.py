from services.video_config import VideoConfig


def should_generate_video(
    *,
    turn_index: int,
    config: VideoConfig,
) -> tuple[bool, str]:
    if not config.enabled:
        return False, "video disabled"

    if config.provider == "none":
        return False, "no video provider configured"

    if config.every_n_turns <= 1:
        return True, "player action"

    if turn_index % config.every_n_turns == 0:
        return True, "scheduled video turn"

    return False, "not scheduled for video"

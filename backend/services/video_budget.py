from dataclasses import dataclass, field


@dataclass
class SessionVideoBudget:
    generated_count: int = 0
    estimated_spend_usd: float = 0.0
    video_urls: list[str] = field(default_factory=list)


def estimate_video_cost_usd(provider: str, width: int, height: int, seconds: int) -> float:
    provider = provider.lower()

    if provider in {"replicate_wan_fast", "replicate_wan_i2v_fast"}:
        if width * height <= 832 * 480:
            return 0.05
        return 0.10

    if provider == "fal_wan_fast":
        return 0.10

    if provider == "fal_ltx_fast":
        return seconds * 0.04

    if provider in {"openrouter_seedance", "openrouter_seedance_i2v"}:
        tokens = (height * width * seconds * 24) / 1024
        return tokens / 1_000_000 * 7.0

    return 999.0


def can_generate_video(
    budget: SessionVideoBudget,
    max_count: int,
    max_spend_usd: float,
    next_cost_usd: float,
) -> tuple[bool, str]:
    if max_count <= 0:
        return False, "video generation disabled by session limit"

    if budget.generated_count >= max_count:
        return False, "session video count limit reached"

    if budget.estimated_spend_usd + next_cost_usd > max_spend_usd:
        return False, "session video spend limit reached"

    return True, "ok"


def record_video_generation(
    budget: SessionVideoBudget,
    video_url: str,
    estimated_cost_usd: float,
) -> None:
    budget.generated_count += 1
    budget.estimated_spend_usd += estimated_cost_usd
    budget.video_urls.append(video_url)

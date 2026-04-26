from __future__ import annotations

import json
from dataclasses import replace

from fastapi import APIRouter, HTTPException

from models import (
    ActionRequest,
    GameSession,
    IdleLoopRequest,
    IdleLoopResponse,
    StartGameRequest,
    TurnResponse,
    VideoBudgetStatus,
    WorldState,
    WorldStatusResponse,
)
from prompts import (
    IDLE_LOOP_PROMPT,
    INITIAL_KEYFRAME_PROMPT,
    WORLD_ENGINE_SYSTEM_PROMPT,
    WORLD_ENGINE_USER_PROMPT_TEMPLATE,
)
from services.game_state import store
from services.scene_observer import observe_scene
from services.video_budget import (
    SessionVideoBudget,
    can_generate_video,
    estimate_video_cost_usd,
    record_video_generation,
)
from services.video_cache import frame_source_hash, get_cached_video, set_cached_video, video_cache_key
from services.video_config import get_video_config
from services.video_decision import should_generate_video
from services.video_provider import VideoGenerationError, generate_video
from services.openrouter import OpenRouterError, generate_initial_keyframe, generate_world_turn
from services.storage import load_starter_frame_data_url, normalize_frame_url

router = APIRouter(prefix="/api", tags=["game"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _build_world_user_prompt(world: WorldState, action_text: str) -> str:
    observation_json = json.dumps(
        world.current_observation.model_dump() if world.current_observation else {}, ensure_ascii=True
    )
    world_json = json.dumps(
        {
            "current_summary": world.current_summary,
            "inventory": world.inventory,
            "memory_tags": world.memory_tags,
            "recent_events": world.recent_events[-8:],
        },
        ensure_ascii=True,
    )
    return WORLD_ENGINE_USER_PROMPT_TEMPLATE.format(
        observation_json=observation_json,
        world_json=world_json,
        player_action=action_text,
    )


def _apply_inventory_delta(inventory: list[str], delta: list[str]) -> list[str]:
    current = [item.strip() for item in inventory if item.strip()]
    for raw in delta:
        entry = raw.strip()
        if not entry:
            continue
        if entry.startswith("-"):
            target = entry[1:].strip().lower()
            current = [item for item in current if item.lower() != target]
            continue
        if entry.startswith("+"):
            entry = entry[1:].strip()
        if entry and all(existing.lower() != entry.lower() for existing in current):
            current.append(entry)
    return current


def _video_budget_status(session: GameSession) -> VideoBudgetStatus:
    return VideoBudgetStatus(
        generated_count=session.video_budget.generated_count,
        estimated_spend_usd=round(session.video_budget.estimated_spend_usd, 4),
        max_session_spend_usd=get_video_config().max_session_spend_usd,
    )


async def maybe_generate_video_for_turn(
    *,
    session: GameSession,
    scene_prompt: str,
    first_frame_url: str | None,
    should_generate: bool,
) -> dict:
    if not should_generate:
        return {
            "scene_video_url": None,
            "video_status": "skipped",
            "video_reason": "world engine disabled video",
            "estimated_video_cost_usd": 0.0,
        }

    config = get_video_config()
    turn_index = int(session.turn)

    should_video, reason = should_generate_video(
        turn_index=turn_index,
        config=config,
    )

    if not should_video:
        return {
            "scene_video_url": None,
            "video_status": "skipped",
            "video_reason": reason,
            "estimated_video_cost_usd": 0.0,
        }

    budget = session.video_budget
    if not isinstance(budget, SessionVideoBudget):
        budget = SessionVideoBudget()
        session.video_budget = budget

    estimated_cost = estimate_video_cost_usd(
        config.provider,
        config.width,
        config.height,
        config.seconds,
    )

    allowed, budget_reason = can_generate_video(
        budget=budget,
        max_count=config.max_per_session,
        max_spend_usd=config.max_session_spend_usd,
        next_cost_usd=estimated_cost,
    )

    if not allowed:
        return {
            "scene_video_url": None,
            "video_status": "skipped",
            "video_reason": budget_reason,
            "estimated_video_cost_usd": estimated_cost,
        }

    cache_key = video_cache_key(
        scene_prompt,
        config.provider,
        config.width,
        config.height,
        config.seconds,
        config.fps,
        frame_source_hash(first_frame_url),
    )

    cached_url = get_cached_video(config.cache_dir, cache_key)
    if cached_url:
        return {
            "scene_video_url": cached_url,
            "video_status": "cached",
            "video_reason": "cache hit",
            "estimated_video_cost_usd": 0.0,
        }

    try:
        video_url = await generate_video(scene_prompt, config, first_frame_url)
    except VideoGenerationError as exc:
        return {
            "scene_video_url": None,
            "video_status": "failed",
            "video_reason": str(exc),
            "estimated_video_cost_usd": 0.0,
        }

    set_cached_video(config.cache_dir, cache_key, video_url)
    record_video_generation(budget, video_url, estimated_cost)

    return {
        "scene_video_url": video_url,
        "video_status": "generated",
        "video_reason": "ok",
        "estimated_video_cost_usd": estimated_cost,
    }


async def generate_idle_loop_video(
    *,
    session: GameSession,
    first_frame_url: str | None,
) -> dict:
    config = get_video_config()
    loop_config = replace(config, seconds=max(1, config.idle_loop_seconds))

    if not loop_config.enabled:
        return {
            "idle_video_url": None,
            "video_status": "skipped",
            "video_reason": "video disabled",
            "estimated_video_cost_usd": 0.0,
        }
    if loop_config.provider == "none":
        return {
            "idle_video_url": None,
            "video_status": "skipped",
            "video_reason": "no video provider configured",
            "estimated_video_cost_usd": 0.0,
        }

    budget = session.video_budget
    if not isinstance(budget, SessionVideoBudget):
        budget = SessionVideoBudget()
        session.video_budget = budget

    estimated_cost = estimate_video_cost_usd(
        loop_config.provider,
        loop_config.width,
        loop_config.height,
        loop_config.seconds,
    )
    allowed, budget_reason = can_generate_video(
        budget=budget,
        max_count=loop_config.max_per_session,
        max_spend_usd=loop_config.max_session_spend_usd,
        next_cost_usd=estimated_cost,
    )
    if not allowed:
        return {
            "idle_video_url": None,
            "video_status": "skipped",
            "video_reason": budget_reason,
            "estimated_video_cost_usd": estimated_cost,
        }

    cache_key = video_cache_key(
        IDLE_LOOP_PROMPT,
        f"{loop_config.provider}:idle",
        loop_config.width,
        loop_config.height,
        loop_config.seconds,
        loop_config.fps,
        frame_source_hash(first_frame_url),
    )
    cached_url = get_cached_video(loop_config.cache_dir, cache_key)
    if cached_url:
        return {
            "idle_video_url": cached_url,
            "video_status": "cached",
            "video_reason": "cache hit",
            "estimated_video_cost_usd": 0.0,
        }

    try:
        video_url = await generate_video(IDLE_LOOP_PROMPT, loop_config, first_frame_url)
    except VideoGenerationError as exc:
        return {
            "idle_video_url": None,
            "video_status": "failed",
            "video_reason": str(exc),
            "estimated_video_cost_usd": 0.0,
        }

    set_cached_video(loop_config.cache_dir, cache_key, video_url)
    record_video_generation(budget, video_url, estimated_cost)
    return {
        "idle_video_url": video_url,
        "video_status": "generated",
        "video_reason": "ok",
        "estimated_video_cost_usd": estimated_cost,
    }


async def _resolve_starter_frame() -> str:
    starter_frame = load_starter_frame_data_url()
    if starter_frame:
        return starter_frame
    return await generate_initial_keyframe(INITIAL_KEYFRAME_PROMPT)


async def _run_turn(session_id: str, action_text: str, supplied_last_frame_url: str | None = None) -> TurnResponse:
    session = store.get_or_create(session_id)

    if supplied_last_frame_url:
        session.scene_image_url = supplied_last_frame_url

    if not session.scene_image_url:
        session.scene_image_url = await _resolve_starter_frame()

    observation = await observe_scene(session.scene_image_url)
    session.world.current_observation = observation

    user_prompt = _build_world_user_prompt(session.world, action_text)
    world_result = await generate_world_turn(WORLD_ENGINE_SYSTEM_PROMPT, user_prompt)

    session.turn += 1
    session.world.current_summary = world_result.updated_world_summary
    session.world.inventory = _apply_inventory_delta(session.world.inventory, world_result.inventory_delta)
    session.world.memory_tags = list(
        dict.fromkeys([*session.world.memory_tags, *world_result.memory_tags])
    )[-32:]
    session.world.recent_events = [
        *session.world.recent_events,
        {"action": action_text, "result": world_result.action_result},
    ][-12:]

    video_result = await maybe_generate_video_for_turn(
        session=session,
        scene_prompt=world_result.video_prompt,
        first_frame_url=session.scene_image_url,
        should_generate=world_result.should_generate_video,
    )
    session.scene_video_url = video_result["scene_video_url"]

    store.save(session)

    return TurnResponse(
        session_id=session.session_id,
        story=world_result.narrator_text,
        choices=[],
        scene_image_url=session.scene_image_url or "/assets/starter.png",
        scene_video_url=video_result["scene_video_url"],
        video_status=video_result["video_status"],
        video_reason=video_result["video_reason"],
        scene_observation=observation,
        estimated_video_cost_usd=video_result["estimated_video_cost_usd"],
        video_budget=_video_budget_status(session),
    )


@router.post("/game/start", response_model=TurnResponse)
async def start_game(req: StartGameRequest) -> TurnResponse:
    try:
        session = store.get_or_create(req.session_id)
        session.turn = 0
        session.world = WorldState()
        session.video_budget = SessionVideoBudget()
        session.scene_video_url = None
        session.scene_image_url = await _resolve_starter_frame()

        observation = await observe_scene(session.scene_image_url)
        session.world.current_observation = observation
        session.world.current_summary = observation.raw_caption

        store.save(session)

        return TurnResponse(
            session_id=session.session_id,
            story=observation.raw_caption,
            choices=[],
            scene_image_url=session.scene_image_url,
            scene_video_url=None,
            video_status="idle",
            video_reason="start scene",
            scene_observation=observation,
            estimated_video_cost_usd=0.0,
            video_budget=_video_budget_status(session),
        )
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/game/action", response_model=TurnResponse)
async def game_action(req: ActionRequest) -> TurnResponse:
    if not req.action_text.strip():
        raise HTTPException(status_code=400, detail="action_text cannot be empty")

    try:
        return await _run_turn(
            session_id=req.session_id,
            action_text=req.action_text.strip(),
            supplied_last_frame_url=normalize_frame_url(req.last_frame_url),
        )
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/game/idle-loop", response_model=IdleLoopResponse)
async def game_idle_loop(req: IdleLoopRequest) -> IdleLoopResponse:
    last_frame_url = normalize_frame_url(req.last_frame_url)
    if not last_frame_url:
        raise HTTPException(status_code=400, detail="last_frame_url cannot be empty")

    session = store.get_or_create(req.session_id)
    session.scene_image_url = last_frame_url

    result = await generate_idle_loop_video(
        session=session,
        first_frame_url=last_frame_url,
    )
    store.save(session)

    return IdleLoopResponse(
        session_id=session.session_id,
        idle_video_url=result["idle_video_url"],
        video_status=result["video_status"],
        video_reason=result["video_reason"],
        estimated_video_cost_usd=result["estimated_video_cost_usd"],
        video_budget=_video_budget_status(session),
    )


@router.get("/game/status", response_model=WorldStatusResponse)
async def world_status() -> WorldStatusResponse:
    return WorldStatusResponse(status="processing", progress_message="The world is reacting...")

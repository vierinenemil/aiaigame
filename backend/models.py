from __future__ import annotations

from pydantic import BaseModel, Field

from services.video_budget import SessionVideoBudget


class SceneObservation(BaseModel):
    location: str
    visible_characters: list[str] = Field(default_factory=list)
    visible_objects: list[str] = Field(default_factory=list)
    mood: str
    lighting: str
    player_perspective: str
    possible_affordances: list[str] = Field(default_factory=list)
    dangers: list[str] = Field(default_factory=list)
    raw_caption: str


class WorldState(BaseModel):
    current_summary: str = ""
    inventory: list[str] = Field(default_factory=list)
    memory_tags: list[str] = Field(default_factory=list)
    recent_events: list[dict[str, str]] = Field(default_factory=list)
    current_observation: SceneObservation | None = None


class GameSession(BaseModel):
    session_id: str
    turn: int = 0
    world: WorldState = Field(default_factory=WorldState)
    scene_image_url: str | None = None
    scene_video_url: str | None = None
    video_budget: SessionVideoBudget = Field(default_factory=SessionVideoBudget)


class StartGameRequest(BaseModel):
    session_id: str


class ActionRequest(BaseModel):
    session_id: str
    action_text: str
    last_frame_url: str | None = None


class IdleLoopRequest(BaseModel):
    session_id: str
    last_frame_url: str


class VideoBudgetStatus(BaseModel):
    generated_count: int
    estimated_spend_usd: float
    max_session_spend_usd: float


class TurnResponse(BaseModel):
    session_id: str
    story: str
    choices: list[str] = Field(default_factory=list)
    scene_image_url: str
    scene_video_url: str | None = None
    video_status: str
    video_reason: str
    scene_observation: SceneObservation | None = None
    estimated_video_cost_usd: float = 0.0
    video_budget: VideoBudgetStatus


class WorldStatusResponse(BaseModel):
    status: str
    progress_message: str


class IdleLoopResponse(BaseModel):
    session_id: str
    idle_video_url: str | None = None
    video_status: str
    video_reason: str
    estimated_video_cost_usd: float = 0.0
    video_budget: VideoBudgetStatus


class WorldTurnDirector(BaseModel):
    narrator_text: str
    action_result: str
    video_prompt: str
    updated_world_summary: str
    inventory_delta: list[str] = Field(default_factory=list)
    memory_tags: list[str] = Field(default_factory=list)
    safety_mode: str = "normal"
    should_generate_video: bool = True

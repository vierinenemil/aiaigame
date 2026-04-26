from __future__ import annotations

from models import SceneObservation
from prompts import SCENE_OBSERVER_PROMPT
from services.openrouter import OpenRouterError, generate_scene_observation


async def observe_scene(image_url: str) -> SceneObservation:
    try:
        return await generate_scene_observation(SCENE_OBSERVER_PROMPT, image_url)
    except OpenRouterError:
        return SceneObservation(
            location="Unclear location",
            visible_characters=[],
            visible_objects=[],
            mood="uncertain",
            lighting="mixed",
            player_perspective="first-person",
            possible_affordances=["look around", "approach nearby figures", "inspect nearby objects"],
            dangers=[],
            raw_caption="You take in the scene and steady yourself before acting.",
        )

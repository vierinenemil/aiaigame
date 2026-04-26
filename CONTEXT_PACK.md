# AI Time-Travel Explorer - Full Context Pack

This document is built for handing the full app context to another model.
It intentionally includes architecture, runtime switches, prompts, backend generation logic, and frontend UX wiring.

## What this app does
- Single-session cinematic time-travel prototype.
- Backend orchestrates story turns with an LLM, and optional video generation with gating.
- Frontend renders image/video scenes, story text, and action buttons returned by the LLM.

## Critical behavior to review
- How story generations are guided (`SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE`, continuity tags).
- How generated turns are accepted/rejected (`response_format`, JSON parsing, fallback choices).
- How video generation is allowed/blocked (moment type, cadence, session budget, provider config, cache).
- How UI buttons are produced from model choices and surfaced to player input.

## Model handoff prompt
Use this with the files below:

> You are reviewing the full architecture and behavior of this project.  
> Trace end-to-end flow from user action -> backend prompt construction -> LLM response parsing -> generation gating -> returned payload -> frontend rendering.  
> Focus especially on:
> 1) how generations are guided,  
> 2) when generations are accepted/rejected,  
> 3) how buttons/choices are generated and displayed,  
> 4) hidden failure modes and consistency bugs,  
> 5) concrete refactors and test additions.  
> Return:
> - A flow diagram (text)
> - Risk list by severity
> - Exact code-level improvements with file names
> - Suggested prompt/schema hardening

---


## File: README.md

```markdown
# AI Time-Travel Explorer (MVP v1.0)

Cinematic branching prototype with one API key via OpenRouter.

## Stack
- Frontend: Next.js 15 + TypeScript + Tailwind
- Backend: FastAPI + httpx
- AI: OpenRouter story + image, optional cheap milestone video via Replicate/fal (Wan fast)

## Project layout
- `frontend/`: full-screen video game UI
- `backend/`: API, game session state, OpenRouter integration

## Prerequisites
- Node 20+
- Python 3.11+
- OpenRouter key

## 1) Environment
```bash
cp .env.example .env
# set OPENROUTER_API_KEY in .env
```

## 2) Run backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 3) Run frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## API endpoints
- `GET /api/health`
- `POST /api/game/start` body: `{ "session_id": "..." }`
- `POST /api/game/action` body: `{ "session_id": "...", "action_text": "...", "last_frame_url": "..." }`

## Notes
- Session store is in-memory for MVP.
- `last_frame_url` currently supports data URLs captured from canvas.
- Replace `services/storage.py` with Blob upload integration for production-grade URL handling.
- Default starter frame uses `assets/starter.png` automatically if present.
- Optional override: set `STARTER_IMAGE_PATH=/absolute/path/to/image.png` in `.env`.
- Story model is configurable via `STORY_MODEL` (default: `x-ai/grok-3-mini`).
- `ENABLE_VIDEO_GENERATION=false` by default, so local dev is image-only and cheap.
- Optional UI-only placeholder while video is disabled: `NEXT_PUBLIC_VIDEO_PLACEHOLDER=true`.
- Recommended cheap premium mode:
  - `VIDEO_PROVIDER=replicate_wan_fast`
  - `VIDEO_WIDTH=832`
  - `VIDEO_HEIGHT=480`
  - `VIDEO_SECONDS=5`
  - `VIDEO_MAX_PER_SESSION=3`
  - `VIDEO_MAX_SESSION_SPEND_USD=0.30`

```

## File: .env.example

```txt
OPENROUTER_API_KEY=sk-or-...
VERCEL_BLOB_TOKEN=
APP_REFERER=http://localhost:3000
APP_TITLE=AI Time-Travel Explorer
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_VIDEO_PLACEHOLDER=true
STARTER_IMAGE_PATH=

# Core story model
STORY_MODEL=x-ai/grok-3-mini

# Video master switch
ENABLE_VIDEO_GENERATION=false

# Cheapest premium video provider
VIDEO_PROVIDER=replicate_wan_fast

# Provider keys
REPLICATE_API_TOKEN=
FAL_KEY=

# Cheap cinematic defaults
VIDEO_WIDTH=832
VIDEO_HEIGHT=480
VIDEO_SECONDS=5
VIDEO_FPS=16
VIDEO_AUDIO=false

# Product gating
VIDEO_MAJOR_MOMENTS_ONLY=true
VIDEO_EVERY_N_TURNS=4
VIDEO_MAX_PER_SESSION=3
VIDEO_MAX_SESSION_SPEND_USD=0.30

# Cache
VIDEO_CACHE_DIR=.cache/videos

```

## File: docker-compose.yml

```yaml
version: '3.9'

services:
  backend:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./backend:/app
    env_file:
      - .env
    command: sh -c "pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000"
    ports:
      - "8000:8000"

  frontend:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./frontend:/app
    env_file:
      - .env
    command: sh -c "npm install && npm run dev"
    ports:
      - "3000:3000"
    depends_on:
      - backend

```

## File: package.json

```json
{
  "name": "ai-time-explorer",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "dev": "node scripts/dev.mjs"
  }
}

```

## File: scripts/dev.mjs

```javascript
import { execSync, spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const rootDir = process.cwd();
const backendDir = path.join(rootDir, "backend");
const frontendDir = path.join(rootDir, "frontend");
const venvDir = path.join(backendDir, ".venv");
const requirementsFile = path.join(backendDir, "requirements.txt");
const requirementsStamp = path.join(venvDir, ".requirements-installed");
const envFile = path.join(rootDir, ".env");

function parseEnvFile(filePath) {
  if (!existsSync(filePath)) return {};
  const parsed = {};
  const lines = readFileSync(filePath, "utf8").split(/\r?\n/);
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim().replace(/^["']|["']$/g, "");
    parsed[key] = value;
  }
  return parsed;
}

const runtimeEnv = {
  ...parseEnvFile(envFile),
  ...process.env,
};

function run(cmd, cwd = rootDir) {
  execSync(cmd, {
    cwd,
    stdio: "inherit",
    shell: "/bin/zsh",
  });
}

function output(cmd, cwd = rootDir) {
  try {
    return execSync(cmd, {
      cwd,
      stdio: ["ignore", "pipe", "ignore"],
      encoding: "utf8",
      shell: "/bin/zsh",
    }).trim();
  } catch {
    return "";
  }
}

function killPort(port) {
  const pids = output(`lsof -ti tcp:${port} -sTCP:LISTEN`);
  if (!pids) return;
  for (const pid of pids.split("\n").filter(Boolean)) {
    try {
      process.kill(Number(pid), "SIGTERM");
    } catch {
      // Ignore stale pids.
    }
  }
}

function ensureBackendReady() {
  if (!existsSync(venvDir)) {
    run("python3 -m venv .venv", backendDir);
  }

  const reqMtime = statSync(requirementsFile).mtimeMs;
  const stampMtime = existsSync(requirementsStamp) ? statSync(requirementsStamp).mtimeMs : 0;
  if (stampMtime < reqMtime) {
    run("source .venv/bin/activate && pip install -r requirements.txt", backendDir);
    writeFileSync(requirementsStamp, String(Date.now()));
  }
}

function ensureFrontendReady() {
  const nodeModulesDir = path.join(frontendDir, "node_modules");
  if (!existsSync(nodeModulesDir)) {
    run("npm install", frontendDir);
  }
}

function startProcess(name, cmd, cwd) {
  const child = spawn("/bin/zsh", ["-lc", cmd], {
    cwd,
    stdio: "inherit",
    env: runtimeEnv,
  });

  child.on("exit", (code, signal) => {
    if (shuttingDown) return;
    shuttingDown = true;
    shutdownChildren();
    const reason = signal ? `signal ${signal}` : `code ${code ?? 0}`;
    console.error(`${name} exited with ${reason}`);
    process.exit(code ?? 1);
  });

  children.push(child);
  return child;
}

const children = [];
let shuttingDown = false;

function shutdownChildren() {
  for (const child of children) {
    if (!child.killed) {
      child.kill("SIGTERM");
    }
  }
}

function main() {
  if (!existsSync(path.join(rootDir, "scripts"))) {
    mkdirSync(path.join(rootDir, "scripts"), { recursive: true });
  }

  killPort(3000);
  killPort(8000);
  ensureBackendReady();
  ensureFrontendReady();

  startProcess(
    "backend",
    "source .venv/bin/activate && uvicorn main:app --host 127.0.0.1 --port 8000",
    backendDir,
  );
  startProcess("frontend", "npm run dev", frontendDir);

  process.on("SIGINT", () => {
    shuttingDown = true;
    shutdownChildren();
    process.exit(0);
  });

  process.on("SIGTERM", () => {
    shuttingDown = true;
    shutdownChildren();
    process.exit(0);
  });
}

main();

```

## File: backend/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.game import router as game_router

app = FastAPI(title="AI Time-Travel Explorer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router)

```

## File: backend/models.py

```python
from __future__ import annotations

from pydantic import BaseModel, Field

from services.video_budget import SessionVideoBudget


class StoryState(BaseModel):
    era: str = "Neutral Hub - Ancient Library"
    character: str = "You are a modern time-traveler"
    task: str = "Retrieve the lost Chrono-Core across 5 eras"
    current_summary: str = "You just arrived through the portal..."
    history: list[dict[str, str]] = Field(default_factory=list)


class GameSession(BaseModel):
    session_id: str
    turn: int = 0
    story: StoryState = Field(default_factory=StoryState)
    scene_image_url: str | None = None
    scene_video_url: str | None = None
    video_budget: SessionVideoBudget = Field(default_factory=SessionVideoBudget)
    visual_continuity_tags: list[str] = Field(default_factory=list)


class StartGameRequest(BaseModel):
    session_id: str


class ActionRequest(BaseModel):
    session_id: str
    action_text: str
    last_frame_url: str | None = None


class VideoBudgetStatus(BaseModel):
    generated_count: int
    estimated_spend_usd: float
    max_session_spend_usd: float


class TurnResponse(BaseModel):
    session_id: str
    story: str
    choices: list[str]
    scene_image_url: str
    scene_video_url: str | None = None
    video_status: str
    video_reason: str
    estimated_video_cost_usd: float = 0.0
    video_budget: VideoBudgetStatus


class WorldStatusResponse(BaseModel):
    status: str
    progress_message: str


class StoryTurnDirector(BaseModel):
    story_text: str
    choices: list[str]
    scene_prompt: str
    visual_continuity_tags: list[str] = Field(default_factory=list)
    moment_type: str = "normal"

```

## File: backend/prompts.py

```python
SYSTEM_PROMPT = """
You are the Game Master for a cinematic time-travel adventure.
Maintain perfect visual and story consistency.
Always respond with valid JSON containing:
- story_text: string narrative for this turn
- choices: array of 3 short action strings
- scene_prompt: cinematic visual prompt for image/video generation, no text or subtitles
- visual_continuity_tags: array of short tags preserving recurring identity, setting, weather, key props
- moment_type: one of normal | milestone | climax | ending

Rules:
- Keep continuity with prior events.
- Prefer concrete visual actions over abstract ideas.
- Keep choices short and player-action oriented.
- Keep JSON valid and without markdown fences.
""".strip()


USER_PROMPT_TEMPLATE = """
Session context:
{story_json}

Player action:
{player_action}

Generate the next turn payload with the required JSON schema.
""".strip()


INITIAL_KEYFRAME_PROMPT = """
Ancient library with a glowing time portal, cinematic realism, moody volumetric light,
subtle dust particles, high detail, filmic composition, protagonist standing near portal.
""".strip()


IDLE_LOOP_PROMPT = """
Subtle seamless idle loop. Exact first frame and exact last frame MUST be identical.
Gentle breathing, wind, flickering light only. No camera movement, no story change,
4 seconds, ambient audio only.
""".strip()

```

## File: backend/routers/game.py

```python
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException

from models import ActionRequest, GameSession, StartGameRequest, TurnResponse, WorldStatusResponse
from prompts import INITIAL_KEYFRAME_PROMPT, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from services.game_state import store
from services.video_budget import (
    SessionVideoBudget,
    can_generate_video,
    estimate_video_cost_usd,
    record_video_generation,
)
from services.video_cache import get_cached_video, set_cached_video, video_cache_key
from services.video_config import get_video_config
from services.video_decision import should_generate_video
from services.video_provider import VideoGenerationError, generate_video
from services.openrouter import (
    OpenRouterError,
    generate_initial_keyframe,
    generate_story_turn,
)
from services.storage import load_starter_frame_data_url, normalize_frame_url

router = APIRouter(prefix="/api", tags=["game"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _build_user_prompt(story: dict, action_text: str) -> str:
    return USER_PROMPT_TEMPLATE.format(
        story_json=json.dumps(story, ensure_ascii=True),
        player_action=action_text,
    )


async def maybe_generate_video_for_turn(
    *,
    session: GameSession,
    story_text: str,
    scene_prompt: str,
    moment_type: str | None,
) -> dict:
    config = get_video_config()
    turn_index = int(session.turn)

    should_video, reason = should_generate_video(
        turn_index=turn_index,
        moment_type=moment_type,
        story_text=story_text,
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
        video_url = await generate_video(scene_prompt, config)
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


async def _run_turn(session_id: str, action_text: str, supplied_last_frame_url: str | None = None) -> TurnResponse:
    session = store.get_or_create(session_id)

    if supplied_last_frame_url:
        session.scene_image_url = supplied_last_frame_url

    if not session.scene_image_url:
        starter_frame = load_starter_frame_data_url()
        if starter_frame:
            session.scene_image_url = starter_frame
        else:
            session.scene_image_url = await generate_initial_keyframe(INITIAL_KEYFRAME_PROMPT)

    prompt_context = {
        **session.story.model_dump(),
        "turn_index": session.turn,
        "visual_continuity_tags": session.visual_continuity_tags,
    }
    user_prompt = _build_user_prompt(prompt_context, action_text)
    story_result = await generate_story_turn(SYSTEM_PROMPT, user_prompt)

    session.turn += 1
    session.story.current_summary = story_result.story_text
    session.story.history.append({"action": action_text, "result": story_result.story_text})
    session.visual_continuity_tags = story_result.visual_continuity_tags

    video_result = await maybe_generate_video_for_turn(
        session=session,
        story_text=story_result.story_text,
        scene_prompt=story_result.scene_prompt,
        moment_type=story_result.moment_type,
    )
    session.scene_video_url = video_result["scene_video_url"]

    store.save(session)

    return TurnResponse(
        session_id=session.session_id,
        story=story_result.story_text,
        choices=story_result.choices,
        scene_image_url=session.scene_image_url or "/assets/starter.png",
        scene_video_url=video_result["scene_video_url"],
        video_status=video_result["video_status"],
        video_reason=video_result["video_reason"],
        estimated_video_cost_usd=video_result["estimated_video_cost_usd"],
        video_budget={
            "generated_count": session.video_budget.generated_count,
            "estimated_spend_usd": round(session.video_budget.estimated_spend_usd, 4),
            "max_session_spend_usd": get_video_config().max_session_spend_usd,
        },
    )


@router.post("/game/start", response_model=TurnResponse)
async def start_game(req: StartGameRequest) -> TurnResponse:
    try:
        return await _run_turn(req.session_id, "begin journey")
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


@router.get("/game/status", response_model=WorldStatusResponse)
async def world_status() -> WorldStatusResponse:
    return WorldStatusResponse(status="processing", progress_message="The world is reacting...")

```

## File: backend/services/openrouter.py

```python
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from models import StoryTurnDirector

load_dotenv()

BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
APP_REFERER = os.getenv("APP_REFERER", "http://localhost:3000")
APP_TITLE = os.getenv("APP_TITLE", "AI Time-Travel Explorer")
IMAGE_MODEL = os.getenv("OPENROUTER_IMAGE_MODEL", "openai/gpt-5.4-image-2")
STORY_MODEL = os.getenv("STORY_MODEL", "x-ai/grok-3-mini")


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

    choices = result.get("choices") or []
    if not choices:
        raise OpenRouterError(f"No choices returned for image generation: {result}")

    message = choices[0].get("message", {})
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


def _normalize_choices(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    choices: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            choices.append(text)
        if len(choices) >= 3:
            break
    return choices


def _normalize_tags(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    tags: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            tags.append(text[:80])
        if len(tags) >= 8:
            break
    return tags


async def generate_story_turn(system_prompt: str, user_prompt: str) -> StoryTurnDirector:
    payload = {
        "model": STORY_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    result = await _post("/chat/completions", payload, timeout=120.0)

    choices = result.get("choices") or []
    if not choices:
        raise OpenRouterError(f"No choices returned: {result}")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise OpenRouterError(f"No content returned: {result}")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"Invalid JSON content from model: {content}") from exc

    story_text = str(parsed.get("story_text", "")).strip()
    scene_prompt = str(parsed.get("scene_prompt", "")).strip()
    choices = _normalize_choices(parsed.get("choices"))
    if len(choices) < 3:
        choices = [
            "Push forward toward the objective",
            "Investigate the most suspicious clue",
            "Retreat to regain control",
        ]

    moment_type = str(parsed.get("moment_type", "normal")).strip().lower()
    if moment_type not in {"normal", "milestone", "climax", "ending"}:
        moment_type = "normal"

    if not story_text:
        raise OpenRouterError(f"story_text missing in model response: {parsed}")
    if not scene_prompt:
        raise OpenRouterError(f"scene_prompt missing in model response: {parsed}")

    return StoryTurnDirector(
        story_text=story_text,
        choices=choices,
        scene_prompt=scene_prompt,
        visual_continuity_tags=_normalize_tags(parsed.get("visual_continuity_tags")),
        moment_type=moment_type,
    )


async def request_video_generation(seedance_prompt: str, first_frame_url: str, last_frame_url: str, duration: int = 8) -> str:
    payload = {
        "model": "bytedance/seedance-2.0",
        "prompt": seedance_prompt,
        "frame_images": [
            {"type": "image_url", "image_url": {"url": first_frame_url}, "frame_type": "first_frame"},
            {"type": "image_url", "image_url": {"url": last_frame_url}, "frame_type": "last_frame"},
        ],
        "duration": duration,
        "resolution": "1080p",
        "generate_audio": True,
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

```

## File: backend/services/game_state.py

```python
from __future__ import annotations

from threading import Lock
from typing import Dict

from models import GameSession


class InMemoryGameStore:
    def __init__(self) -> None:
        self._data: Dict[str, GameSession] = {}
        self._lock = Lock()

    def get_or_create(self, session_id: str) -> GameSession:
        with self._lock:
            if session_id not in self._data:
                self._data[session_id] = GameSession(session_id=session_id)
            return self._data[session_id]

    def get(self, session_id: str) -> GameSession | None:
        with self._lock:
            return self._data.get(session_id)

    def save(self, session: GameSession) -> None:
        with self._lock:
            self._data[session.session_id] = session


store = InMemoryGameStore()

```

## File: backend/services/storage.py

```python
from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

# Storage abstraction placeholder.
# For MVP, frame URLs can be data URLs or already-hosted URLs from frontend.


def normalize_frame_url(frame_url: str | None) -> str | None:
    if not frame_url:
        return None
    return frame_url.strip()


def load_starter_frame_data_url() -> str | None:
    configured = os.getenv("STARTER_IMAGE_PATH", "").strip()
    if configured:
        image_path = Path(configured)
    else:
        image_path = Path(__file__).resolve().parents[2] / "assets" / "starter.png"

    if not image_path.exists() or not image_path.is_file():
        return None

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type:
        mime_type = "image/png"

    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"

```

## File: backend/services/video_config.py

```python
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
        audio=env_bool("VIDEO_AUDIO", False),
        major_moments_only=env_bool("VIDEO_MAJOR_MOMENTS_ONLY", True),
        every_n_turns=max(1, env_int("VIDEO_EVERY_N_TURNS", 4)),
        max_per_session=max(0, env_int("VIDEO_MAX_PER_SESSION", 3)),
        max_session_spend_usd=max(0.0, env_float("VIDEO_MAX_SESSION_SPEND_USD", 0.30)),
        cache_dir=os.getenv("VIDEO_CACHE_DIR", ".cache/videos"),
    )

```

## File: backend/services/video_decision.py

```python
from services.video_config import VideoConfig


def should_generate_video(
    *,
    turn_index: int,
    moment_type: str | None,
    story_text: str,
    config: VideoConfig,
) -> tuple[bool, str]:
    if not config.enabled:
        return False, "video disabled"

    if config.provider == "none":
        return False, "no video provider configured"

    normalized_moment = (moment_type or "normal").lower()

    if normalized_moment in {"milestone", "climax", "ending"}:
        return True, "major story moment"

    if config.major_moments_only:
        return False, "not a major story moment"

    if turn_index % config.every_n_turns == 0:
        return True, "scheduled video turn"

    return False, "not scheduled for video"

```

## File: backend/services/video_budget.py

```python
from dataclasses import dataclass, field


@dataclass
class SessionVideoBudget:
    generated_count: int = 0
    estimated_spend_usd: float = 0.0
    video_urls: list[str] = field(default_factory=list)


def estimate_video_cost_usd(provider: str, width: int, height: int, seconds: int) -> float:
    provider = provider.lower()

    if provider == "replicate_wan_fast":
        if width * height <= 832 * 480:
            return 0.05
        return 0.10

    if provider == "fal_wan_fast":
        return 0.10

    if provider == "fal_ltx_fast":
        return seconds * 0.04

    if provider == "openrouter_seedance":
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

```

## File: backend/services/video_cache.py

```python
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
) -> str:
    raw = json.dumps(
        {
            "prompt": prompt,
            "provider": provider,
            "width": width,
            "height": height,
            "seconds": seconds,
            "fps": fps,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


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

```

## File: backend/services/video_provider.py

```python
import os
from typing import Any

from services.video_config import VideoConfig


class VideoGenerationError(Exception):
    pass


def clean_prompt(prompt: str) -> str:
    return " ".join(prompt.strip().split())[:900]


async def generate_video(prompt: str, config: VideoConfig) -> str:
    provider = config.provider.lower()

    if provider == "replicate_wan_fast":
        return await generate_replicate_wan_fast(prompt, config)

    if provider == "fal_wan_fast":
        return await generate_fal_wan_fast(prompt, config)

    if provider == "fal_ltx_fast":
        return await generate_fal_ltx_fast(prompt, config)

    raise VideoGenerationError(f"Unsupported video provider: {provider}")


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


def extract_video_url(output: Any) -> str:
    if isinstance(output, str):
        return output

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

```

## File: backend/scripts/step1_verify_seedance.py

```python
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

```

## File: frontend/package.json

```json
{
  "name": "ai-time-explorer-frontend",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "15.2.3",
    "react": "19.0.0",
    "react-dom": "19.0.0"
  },
  "devDependencies": {
    "@types/node": "22.13.11",
    "@types/react": "19.0.10",
    "@types/react-dom": "19.0.4",
    "autoprefixer": "10.4.20",
    "postcss": "8.5.3",
    "tailwindcss": "3.4.17",
    "typescript": "5.8.2"
  }
}

```

## File: frontend/app/page.tsx

```tsx
import VideoPlayer from "@/components/VideoPlayer";

export default function HomePage() {
  return <VideoPlayer />;
}

```

## File: frontend/components/VideoPlayer.tsx

```tsx
"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import ActionOverlay from "@/components/ActionOverlay";
import LoopingIdle from "@/components/LoopingIdle";
import { extractCurrentFrame, makeSessionId } from "@/lib/utils";

type TurnResponse = {
  session_id: string;
  story: string;
  choices: string[];
  scene_image_url: string;
  scene_video_url: string | null;
  video_status: string;
  video_reason: string;
  estimated_video_cost_usd: number;
};

function isImageMedia(url: string | null) {
  if (!url) return false;
  return (
    url.startsWith("data:image/") ||
    /\.(png|jpg|jpeg|webp|gif)(\?|$)/i.test(url) ||
    url.includes("image/")
  );
}

export default function VideoPlayer() {
  const placeholderVideoEnabled = process.env.NEXT_PUBLIC_VIDEO_PLACEHOLDER === "true";
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [sessionId] = useState(() => makeSessionId());
  const [started, setStarted] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  const [sceneVideoUrl, setSceneVideoUrl] = useState<string | null>(null);
  const [sceneImageUrl, setSceneImageUrl] = useState<string | null>(null);
  const [lastFrameDataUrl, setLastFrameDataUrl] = useState<string | null>(null);
  const [buttons, setButtons] = useState<string[]>([]);
  const [storyText, setStoryText] = useState<string | null>(null);
  const [videoStatus, setVideoStatus] = useState<string | null>(null);
  const [videoReason, setVideoReason] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const showVideoPlaceholder = placeholderVideoEnabled && !sceneVideoUrl && !!sceneImageUrl;
  const statusText = useMemo(() => (isGenerating ? "The world is reacting..." : ""), [isGenerating]);

  async function callTurn(path: string, payload: Record<string, unknown>) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const raw = await res.text();
      try {
        const parsed = JSON.parse(raw) as { detail?: string };
        throw new Error(parsed.detail || raw || "Request failed");
      } catch {
        throw new Error(raw || "Request failed");
      }
    }

    const data = (await res.json()) as TurnResponse;
    setSceneImageUrl(data.scene_image_url);
    setSceneVideoUrl(data.scene_video_url);
    setButtons(data.choices);
    setStoryText(data.story);
    setVideoStatus(data.video_status);
    setVideoReason(data.video_reason);
    if (!data.scene_video_url) {
      setLastFrameDataUrl(data.scene_image_url);
      setShowOverlay(true);
    } else {
      setShowOverlay(false);
    }
  }

  const startJourney = async () => {
    setStarted(true);
    setIsGenerating(true);
    setErrorMessage(null);
    try {
      await callTurn("/api/game/start", { session_id: sessionId });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start journey");
      setStarted(false);
    } finally {
      setIsGenerating(false);
    }
  };

  const onAction = async (actionText: string) => {
    setIsGenerating(true);
    setShowOverlay(false);
    setErrorMessage(null);

    try {
      await callTurn("/api/game/action", {
        session_id: sessionId,
        action_text: actionText,
        last_frame_url: lastFrameDataUrl,
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to continue journey");
      setShowOverlay(true);
    } finally {
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    if (!videoRef.current || !sceneVideoUrl || isImageMedia(sceneVideoUrl)) return;
    const video = videoRef.current;
    video.src = sceneVideoUrl;
    void video.play();
  }, [sceneVideoUrl]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onEnded = async () => {
      try {
        const dataUrl = await extractCurrentFrame(video);
        setLastFrameDataUrl(dataUrl);
      } catch {
        setLastFrameDataUrl(null);
      }
      setShowOverlay(true);
    };

    video.addEventListener("ended", onEnded);
    return () => video.removeEventListener("ended", onEnded);
  }, []);

  return (
    <div className="relative h-screen w-screen overflow-hidden">
      {!isImageMedia(sceneVideoUrl) && sceneVideoUrl && (
        <video
          ref={videoRef}
          className="absolute inset-0 h-full w-full object-cover"
          autoPlay
          playsInline
          controls={false}
        />
      )}

      {(!sceneVideoUrl || isImageMedia(sceneVideoUrl)) && sceneImageUrl && (
        <img src={sceneImageUrl} alt="Scene" className="absolute inset-0 h-full w-full object-cover" />
      )}

      {showVideoPlaceholder && (
        <div className="pointer-events-none absolute inset-0 z-10">
          <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/15 via-transparent to-amber-500/15" />
          <div className="absolute right-4 bottom-4 rounded-md border border-white/30 bg-black/60 px-3 py-1 text-xs text-white">
            Video Placeholder Mode
          </div>
        </div>
      )}

      <LoopingIdle imageDataUrl={lastFrameDataUrl} active={showOverlay || isGenerating} />

      {!started && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/40">
          <button
            onClick={startJourney}
            className="rounded-2xl border border-mist/30 bg-portal/80 px-8 py-4 text-lg font-semibold text-black shadow-2xl transition hover:brightness-110"
          >
            Begin Your Journey
          </button>
        </div>
      )}

      {statusText && (
        <div className="absolute inset-x-0 top-0 z-30 mx-auto mt-5 w-fit rounded-full border border-mist/20 bg-ink/70 px-4 py-2 text-sm text-mist">
          {statusText}
        </div>
      )}

      {errorMessage && (
        <div className="absolute inset-x-0 top-20 z-30 mx-auto max-w-2xl rounded-xl border border-red-400/30 bg-red-950/85 px-4 py-3 text-sm text-red-100 shadow-xl">
          {errorMessage}
        </div>
      )}

      {process.env.NODE_ENV === "development" && videoStatus && (
        <div className="absolute right-4 top-4 z-30 rounded bg-black/70 px-3 py-2 text-xs text-white">
          Video: {videoStatus} - {videoReason}
        </div>
      )}

      {storyText && (
        <div className="absolute left-4 top-4 z-20 max-w-md rounded-xl border border-mist/15 bg-ink/60 p-3 text-xs text-mist/85 backdrop-blur-sm">
          <div>{storyText}</div>
        </div>
      )}

      {showOverlay && <ActionOverlay buttons={buttons} disabled={isGenerating} onSubmit={onAction} />}
    </div>
  );
}

```

## File: frontend/components/ActionOverlay.tsx

```tsx
"use client";

import { FormEvent, useMemo, useState } from "react";

type Props = {
  buttons: string[];
  disabled?: boolean;
  onSubmit: (value: string) => void;
};

export default function ActionOverlay({ buttons, disabled = false, onSubmit }: Props) {
  const [value, setValue] = useState("");
  const shownButtons = useMemo(() => buttons.slice(0, 5), [buttons]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  return (
    <div className="absolute inset-x-0 bottom-0 z-20 bg-gradient-to-t from-black/75 to-transparent p-4 md:p-8">
      <div className="mx-auto max-w-3xl rounded-2xl border border-mist/20 bg-ink/60 p-4 backdrop-blur-md">
        <div className="mb-3 flex flex-wrap gap-2">
          {shownButtons.map((buttonText) => (
            <button
              key={buttonText}
              type="button"
              disabled={disabled}
              className="rounded-full border border-portal/60 bg-portal/20 px-4 py-2 text-sm text-mist transition hover:bg-portal/35 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={() => onSubmit(buttonText)}
            >
              {buttonText}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="flex gap-2">
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={disabled}
            placeholder="What do you do next?"
            className="flex-1 rounded-xl border border-mist/30 bg-black/40 px-4 py-3 text-sm text-mist placeholder:text-mist/50 outline-none focus:border-portal"
          />
          <button
            type="submit"
            disabled={disabled}
            className="rounded-xl bg-portal px-4 py-3 text-sm font-medium text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

```

## File: frontend/components/LoopingIdle.tsx

```tsx
"use client";

type Props = {
  imageDataUrl: string | null;
  active: boolean;
};

export default function LoopingIdle({ imageDataUrl, active }: Props) {
  if (!active || !imageDataUrl) return null;

  return (
    <img
      src={imageDataUrl}
      alt="Idle frame"
      className="absolute inset-0 h-full w-full animate-pulse object-cover opacity-85"
    />
  );
}

```

## File: frontend/lib/utils.ts

```tsx
export async function extractCurrentFrame(video: HTMLVideoElement): Promise<string> {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth || 1920;
  canvas.height = video.videoHeight || 1080;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas context unavailable");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/png");
}

export function makeSessionId(): string {
  return `session_${Math.random().toString(36).slice(2)}_${Date.now()}`;
}

```

## File: frontend/app/api/game/[...path]/route.ts

```tsx
import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

function buildTargetUrl(path: string[]) {
  const cleaned = path.filter(Boolean).map(encodeURIComponent).join("/");
  return `${BACKEND_BASE}/api/game/${cleaned}`;
}

async function forward(req: NextRequest, path: string[]) {
  const target = buildTargetUrl(path);
  const body = req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers: {
        "Content-Type": req.headers.get("content-type") ?? "application/json",
      },
      body,
      cache: "no-store",
    });

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown proxy error";
    return NextResponse.json(
      {
        detail: `Backend request failed via Next proxy: ${detail}`,
        target,
      },
      { status: 502 },
    );
  }
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return forward(req, path);
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return forward(req, path);
}

```

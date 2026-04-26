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

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_FILE="${1:-$ROOT_DIR/CONTEXT_PACK.md}"

FILES=(
  "README.md"
  ".env.example"
  "docker-compose.yml"
  "package.json"
  "scripts/dev.mjs"
  "backend/main.py"
  "backend/models.py"
  "backend/prompts.py"
  "backend/routers/game.py"
  "backend/services/openrouter.py"
  "backend/services/game_state.py"
  "backend/services/storage.py"
  "backend/services/video_config.py"
  "backend/services/video_decision.py"
  "backend/services/video_budget.py"
  "backend/services/video_cache.py"
  "backend/services/video_provider.py"
  "backend/scripts/step1_verify_seedance.py"
  "frontend/package.json"
  "frontend/app/page.tsx"
  "frontend/components/VideoPlayer.tsx"
  "frontend/components/ActionOverlay.tsx"
  "frontend/components/LoopingIdle.tsx"
  "frontend/lib/utils.ts"
  "frontend/app/api/game/[...path]/route.ts"
)

cat > "$OUT_FILE" <<'HEADER'
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

HEADER

for rel in "${FILES[@]}"; do
  abs="$ROOT_DIR/$rel"
  if [[ ! -f "$abs" ]]; then
    continue
  fi

  ext="${rel##*.}"
  lang="txt"
  case "$ext" in
    py) lang="python" ;;
    ts|tsx) lang="tsx" ;;
    js|mjs) lang="javascript" ;;
    json) lang="json" ;;
    md) lang="markdown" ;;
    yml|yaml) lang="yaml" ;;
    *) lang="txt" ;;
  esac

  {
    printf "\n## File: %s\n\n" "$rel"
    printf '```%s\n' "$lang"
    cat "$abs"
    printf '\n```\n'
  } >> "$OUT_FILE"
done

printf 'Wrote %s\n' "$OUT_FILE"

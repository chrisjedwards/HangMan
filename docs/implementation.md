<!-- DRAFT: review and rewrite in your own words before submitting -->

# Phase 2: Implementation

This document records what is actually built during Phase 2. It currently contains plans only.

## Planned architecture

Browser -> Nginx -> Gunicorn/Flask -> Bedrock

The server will own each game's secret word and the frontend will communicate through the API contract.

## Backend (Chris)

Status: mock complete, Bedrock not started

### What was actually built

The Flask backend implements the full [API contract](api_contract.md) in mock
mode (`MOCK_AI=true`, the default): `app.py` (application factory, JSON error
handlers for 404/405/429/500, dev-mode static serving of `../frontend` at
`/`), `config.py` (env-based config), `services/game_state.py` (in-memory,
thread-safe `GameStore` with masking, guess handling, win/lose, hint limits,
~2h game expiry, and a max-games cap), `services/words.py` (fallback word
selection avoiding recently used words), `services/ai.py` (`MockAI` with
canned, varied word/hint/comment responses; `BedrockAI` is a stub that raises
`NotImplementedError`), `utils/validators.py` and `utils/errors.py`, and
`routes/game.py` / `routes/health.py`. Rate limiting uses Flask-Limiter,
configured from `RATE_LIMIT`.

58 automated tests (pytest, `backend/tests/`) cover game logic, validators,
and every endpoint through the Flask test client, including error cases and a
dedicated test that the secret word never appears in any response before the
game is over.

**Design decision - single gunicorn worker:** game state lives only in this
process's memory (there is no database or shared cache), so production must
run gunicorn with exactly one worker (`--workers 1 --threads 4`). With more
than one worker, a `game_id` created on one worker's memory would not exist
in another worker's memory, and requests for it would incorrectly return
`game_not_found`. This is a known limitation, not a bug: scaling beyond one
process would require moving game state into a shared store (e.g. Redis),
which is out of scope for this project.

Verified 2026-09-22, from `backend/` with `MOCK_AI=true`:

- Fresh venv + `pip install -r requirements.txt` succeeded.
- `python3 -m pytest` - 58 passed.
- Flask dev server (`python3 app.py`): full curl session through a complete
  winning game and a complete losing game (word revealed only after game
  over in both cases), hint limit enforcement, and all documented error
  shapes (`invalid_request`, `game_not_found`, `not_found`,
  `method_not_allowed`, `rate_limited`).
- `gunicorn --workers 1 --threads 4 "app:create_app()"` started cleanly and
  answered `GET /api/health` with `{"status": "ok"}`.

### Problems and solutions

See `docs/devlog.md` for the dated entry on the `/api/*` routing bug found
and fixed while building this (unmatched API paths were briefly returning
the frontend's `200` fallback instead of a JSON `404`).

## AI integration (Chris)

Status: not started

### What was actually built

### Problems and solutions

## Frontend (Gaby)

Status: not started

### What was actually built

### Problems and solutions

## Deployment (Chris)

Status: not started

### What was actually built

### Problems and solutions

## Problems and solutions

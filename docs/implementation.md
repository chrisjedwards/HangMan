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

Status: complete

### What was actually built

`services/ai.py`'s `BedrockAI` calls AWS Bedrock's Converse API
(`bedrock-runtime` client, `region_name`/`modelId` from `config.py`, no
hardcoded credentials - boto3 picks up local CLI credentials or, on EC2, the
instance profile). The three prompt templates in `backend/prompts/*.md` are
parsed into a (system prompt, user template) pair once at construction time
(not per-request), then filled with `{{placeholder}}` substitution per call.

Guards: a request timeout (`BEDROCK_TIMEOUT_SECONDS`, default 8s) and
`maxTokens` cap (`BEDROCK_MAX_TOKENS`, default 200) from `config.py`; a
single retry on a transient error only (a network timeout or a Bedrock error
code in `TRANSIENT_ERROR_CODES` such as `ThrottlingException`) - a
validation failure is never retried, since retrying a broken answer just
spends money asking the same question again.

The model is asked to return JSON only; the response is parsed defensively
(a markdown code fence around the JSON, if the model adds one despite being
told not to, is stripped before `json.loads`). Every word is checked with
`utils.validators.validate_ai_word` and every hint with
`hint_contains_word` - the same functions the routes already trusted for
`MockAI` - before it can reach a route. Any failure (invalid JSON, an
invalid word, a hint that leaks the secret word, or an exhausted retry)
raises a single `AIError`, which the routes catch specifically (never a bare
`Exception`, so a genuine bug still surfaces as a 500):

- `generate-word` falls back to `fallback_words.json` on `AIError`, per the
  fallback-words safeguard in CLAUDE.md.
- `hint` and `comment` have no invented fallback text: an `AIError` (or a
  hint that still leaks the word despite BedrockAI's own check - a
  defense-in-depth check in the route) returns
  `{"error":{"code":"ai_unavailable",...}}` with HTTP 502, so the player is
  never shown text presented as AI-authored that the AI didn't actually say.

22 new automated tests were added on top of the existing 58 (80 total,
pytest, `backend/tests/`), still run with `MOCK_AI=true` (no AWS cost, no
network dependency): `tests/test_ai.py` unit-tests `BedrockAI` directly
against a hand-written stub `bedrock-runtime` client (happy path for all
three calls, invalid JSON, an invalid/wrong-length word, a leaking hint, a
non-transient error with no retry, and a transient/timeout error retried
exactly once then failing or succeeding); `tests/test_ai_fallback_routes.py`
covers the same failures at the route level with a fake `AIProvider`
(fallback to `fallback_words.json`, both AI endpoints returning 502
`ai_unavailable`, and confirming a leaking hint never reaches the client).
Verified 2026-09-22: `python3 -m pytest` - 80 passed, run three times with
no flakiness.

Real Bedrock verification was first attempted 2026-09-22 with `MOCK_AI=false`
against `eu.anthropic.claude-haiku-4-5-20251001-v1:0` in `eu-north-1` and
initially blocked by `ResourceNotFoundException` (an AWS account-side setup
step, not a code bug - see `docs/devlog.md`). After that was resolved, a
second real run the same day completed a full game end to end with actual
model output:

- `generate-word` (programming_languages/medium): model returned `golang`
  (lowercase, plus extra fields beyond the documented schema such as
  `starts_with` and an unrequested `hint`); correctly normalized to
  `GOLANG` and validated. Usage: 67 input / 68 output / 135 total tokens.
- `hint`: "This language was created by Google and is known for its
  simplicity, fast compilation, and built-in support for concurrent
  programming." - useful, did not leak the word. Usage: 67 input / 52
  output / 119 total tokens.
- `comment` (after winning): "Perfect game! You solved GOLANG without a
  single wrong guess and still had 6 lives to spare. That's some serious
  tech prowess! Go(lang) celebrate your victory!" Usage: 89 input / 65
  output / 154 total tokens.
- Total: 408 tokens across the 3 real calls for one full game.

The model wrapped every response in a ```json markdown fence despite the
system prompt saying "Return JSON only" - confirming the defensive
fence-stripping in `_parse_json_response` was a real, not speculative,
safeguard. Both `generate-word`'s validation (accepting the lowercase word
after normalizing) and `hint`'s leak check passed correctly against real
model output, not just the mocked stub used in `tests/test_ai.py`.
Real end-to-end verification with actual model output is still pending
until the AWS use case form is submitted and access is confirmed.

**Known limitation - hint attempt spent on AI failure:** `hint`'s
hints-used counter is incremented before calling the AI, so a player who
hits an `ai_unavailable` error still loses that hint attempt. Fixing this
would need a "refund the hint" path, which risks a race against a concurrent
request for the same game for a benefit that's marginal here (Bedrock
failures are expected to be rare). Accepted as-is rather than added
speculatively.

### Problems and solutions

## Frontend (Gaby)

Status: initial build complete, PR open for review, not yet merged

### What was actually built

The frontend was implemented as plain HTML, CSS, and vanilla JavaScript under
`frontend/` — no framework, no build step, mobile-first — matching the
[API contract](api_contract.md): `index.html` (three screens: setup, game,
end), `style.css` (dark theme, responsive layout, SVG hangman styling), and
`script.js` (all fetch calls to `/api/generate-word`, `/api/guess`,
`/api/hint`, `/api/comment`).

The game state (masked word, lives left, wrong letters, status) is never
stored or guessed client-side — every screen update comes directly from the
backend's JSON response. The client only tracks which letters the player has
already clicked, to disable those keyboard buttons locally.

The hangman figure is drawn as inline SVG, with each body part (`part-head`,
`part-body`, `part-arm-left`, `part-arm-right`, `part-leg-left`,
`part-leg-right`) revealed incrementally based on `lives_left` versus
`max_lives` from the `/api/guess` response.

All three files were reviewed against `docs/api_contract.md` field by field
(request/response shapes for all four endpoints) before being committed, to
confirm the frontend and the documented contract stay in sync.

Committed and pushed to branch `gaby/frontend`
(`git add frontend/`, `git commit`, `git push -u origin gaby/frontend`), with
a pull request opened against `main`, awaiting review before merge.

### Problems and solutions

No functional issues encountered yet during this initial build. One
cosmetic note: Git on Windows warned that LF line endings would be
converted to CRLF on commit (`warning: LF will be replaced by CRLF`) — this
is expected behavior on Windows and required no fix.


## Deployment (Chris)

Status: not started

### What was actually built

### Problems and solutions

## Problems and solutions

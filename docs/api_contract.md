<!-- DRAFT: review and rewrite in your own words before submitting -->

# API Contract

This document is the synchronization point between Chris's backend and Gaby's frontend. The contract is planned and can be used to build the frontend against `MOCK_AI=true` once the backend exists.

## General rules

- Requests and responses use JSON.
- The backend stores the secret word by `game_id`.
- The secret word is never returned before game over.
- AI input is structured server-side data; no user-typed text is sent to the model.
- Errors use `{"error":{"code":"...","message":"..."}}` and an appropriate HTTP status.

## POST /api/generate-word

Request:

```json
{ "category": "programming_languages", "difficulty": "medium" }
```

Response `200`:

```json
{
  "game_id": "abc123",
  "length": 6,
  "category": "programming_languages",
  "difficulty": "medium",
  "max_lives": 6
}
```

The response does not include the secret word.

## POST /api/guess

Request:

```json
{ "game_id": "abc123", "letter": "P" }
```

Response `200` while playing:

```json
{
  "masked_word": "P _ _ _ _ _",
  "correct": true,
  "wrong_letters": [],
  "lives_left": 6,
  "status": "playing"
}
```

Response `200` after game over:

```json
{
  "masked_word": "P Y T H O N",
  "correct": true,
  "wrong_letters": ["Z"],
  "lives_left": 4,
  "status": "won",
  "word": "PYTHON"
}
```

`word` is included only when `status` is `won` or `lost`.

## POST /api/hint

Request:

```json
{ "game_id": "abc123" }
```

Response `200`:

```json
{
  "hint": "It is commonly used to automate tasks and build web applications.",
  "hints_left": 1
}
```

The endpoint is limited by `MAX_HINTS`.

## POST /api/comment

Request:

```json
{ "game_id": "abc123" }
```

Response `200` after game over:

```json
{ "comment": "Nice debugging run. Your code survived the final test!" }
```

This endpoint is rejected before the game is over.

## GET /api/health

Response `200`:

```json
{ "status": "ok" }
```

## Error examples

Malformed or invalid input:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "category and difficulty are required"
  }
}
```

Unknown game:

```json
{
  "error": {
    "code": "game_not_found",
    "message": "The game does not exist or has expired"
  }
}
```

Rate limited:

```json
{ "error": { "code": "rate_limited", "message": "Too many requests" } }
```

## Validation expectations

The backend will validate categories, difficulties, game IDs, single A-Z letters, game status, hint limits, and model output. It will use fallback words if word generation fails or produces an invalid word. Timeouts and maximum model tokens are planned safeguards.

<!-- DRAFT: review and rewrite in your own words before submitting -->

# Phase 3: Finalization

## Testing

Status: local testing complete, AWS deployment pending

**Automated:** `python3 -m pytest` in `backend/tests/` — 80 tests passing,
covering game logic, validators, routes, and the AI layer (against a mocked
boto3 client, no real network calls).

**Manual, mock mode (`MOCK_AI=true`):** Started the Flask dev server and
played a full game through the actual browser UI at `http://127.0.0.1:5000`
(Chrome) — category/difficulty selection, letter guesses, a hint, both a win
screen and a loss screen, and the AI comment. Verified via DevTools' Network
tab that every request (`generate-word`, `guess`, `hint`, `comment`)
returned `200`, with no failed calls.

**Manual, real Bedrock (`MOCK_AI=false`):** Ran a full game through the real
API end to end (`generate-word`, guesses, `hint`, `comment`) against live
Bedrock. The secret word (`FORTRAN`) never appeared in any response before
game over, the hint never contained the word, and the AI comment was
on-topic. Token usage: 397 tokens total across the three AI calls (~$0.0011).

**Cross-check after merge:** After merging the frontend (`gaby/frontend`)
into `main`, the frontend was tested against the backend and the full
pytest suite was re-run — still 80/80 passing, confirming the merge didn't
break backend behavior.

Not yet tested: deployment to AWS. No public URL has been tested.

## Improvements and optimization

## Deployment and publication

## Problems and solutions

<!-- DRAFT: review and rewrite in your own words before submitting -->

# Conclusion

## What we achieved

- Built the full frontend (setup, game, and end screens) in plain HTML, CSS, and vanilla JavaScript — mobile-first, no framework, no build step — matching `docs/api_contract.md` exactly.
- Made sure all game state (masked word, lives, wrong letters, status) comes from the backend on every request; the client never stores or guesses the secret word.
- Manually verified all four API endpoints against the documented contract before writing any UI code, then browser-tested the full game loop (guessing, hints, winning, losing, the AI comment) against the real backend.
- Renamed the project from the generic "AI Hangman" to "HangDev" and updated the footer credit to "// made by Gaby & Chris" instead of "school project", for a more polished, personal presentation.
- Got the frontend PR merged into `main`, and the finished app is now deployed and confirmed working live at http://51.20.142.127/.

## What we learned

- How valuable a written API contract is for splitting frontend/backend work in parallel — it let the frontend be built and tested against `MOCK_AI=true` without needing to read or wait on the backend's implementation.
- Real differences between Mac and Windows local setup (Python launcher name, PowerShell execution policy, venv activation syntax) that the original Mac-written instructions didn't cover.
- The importance of testing a frontend against its real backend origin rather than a generic static server, since a same-origin mismatch produces confusing errors that look like backend bugs.

## What could be improved

- The frontend currently has no automated tests — only manual/browser verification. Adding a small Playwright suite would catch regressions faster than repeating manual click-throughs.
- Accessibility is a partial pass (physical-keyboard play and `aria-live` regions are in, but the SVG hangman figure and some live-region labelling could go further).
- Category and difficulty options are hardcoded in the UI; if the backend ever exposed this as metadata, the frontend could render it dynamically instead.

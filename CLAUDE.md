<!-- DRAFT: review and rewrite in your own words before submitting -->

# AI Hangman Project Context

## Project

AI Hangman is a planned English-language web game with a programming and technology theme. Chris and Gaby are building it for a school GenAI assignment.

## Decisions

- Backend: Python, Flask, boto3 Bedrock Converse API, Gunicorn, and Flask-Limiter.
- Frontend: plain mobile-first HTML, CSS, and JavaScript with no framework or build step.
- AI: one Claude model on AWS Bedrock, used through three separate endpoints and prompts.
- Hosting: EC2 with Nginx in front of Gunicorn, provisioned through Terraform and cloud-init.
- The application will use an IAM instance profile on EC2. Local work can use AWS CLI credentials or `MOCK_AI=true`.
- Model ID and region remain configurable through environment variables.

## AI design

- No user-typed text is sent to the model. Requests use structured server-selected fields.
- The secret word is stored server-side per `game_id` and is withheld from the client until game over.
- The three AI tasks are word generation, hints, and end-of-game comments.
- Backend validation, fallback words, rate limits, token caps, timeouts, and clean JSON errors are planned safeguards.

## API

The frontend/backend synchronization contract is documented in [`docs/api_contract.md`](docs/api_contract.md).

## Ownership

- Chris: backend, AI integration, prompts, AWS deployment, and Phase 1-3 documentation.
- Gaby: frontend, UI, game mechanics, testing, Phase 2 and Phase 4 documentation, and conclusion.
- Shared: prompt testing, frontend/backend synchronization, AWS testing, video, and final push.

## Working rules

- Keep documentation in English.
- Start drafted documents with the required draft marker.
- Do not claim work is built, tested, fixed, or deployed until it has actually happened.
- Record real problems in `docs/devlog.md` before compiling them elsewhere.
- Never commit secrets or `.env`.
- Use small branches named `chris/<topic>` or `gaby/<topic>` and review each other's pull requests.
- Do not commit or push without reviewing the changes together.

<!-- DRAFT: review and rewrite in your own words before submitting -->

# AI Hangman

AI Hangman is a planned web-based Hangman game with a programming and technology theme. Chris and Gaby are developing it for a school GenAI assignment. Generative AI is intended to be a central feature, while the server keeps the secret word private until the game ends.

## Planned features

- English Hangman gameplay.
- Programming, DevOps, AWS, and Linux word categories.
- Easy, medium, and hard difficulty levels.
- AI-generated words, hints, and end-of-game comments.
- Mock AI mode for local frontend work without AWS access.
- Rate limiting, validation, timeouts, token caps, and fallback words.
- Public AWS deployment through EC2 and Nginx.

## Technology stack

- Backend: Python, Flask, boto3 Bedrock Converse API, Gunicorn, Flask-Limiter.
- Frontend: plain HTML, CSS, and JavaScript; mobile-first; no framework or build step.
- Hosting: AWS EC2, Nginx, systemd, Terraform, and cloud-init.
- AI: one Claude model on AWS Bedrock.

## Planned architecture

```text
Browser -> Nginx -> Gunicorn/Flask -> AWS Bedrock
```

Nginx will serve the frontend and proxy `/api/` to Gunicorn on `127.0.0.1`, keeping the browser and API on the same origin. On EC2, the application is planned to use an IAM instance profile instead of API keys.

The frontend/backend synchronization contract is [docs/api_contract.md](docs/api_contract.md).

## Project structure

```text
backend/       Flask application, services, prompts, fallback data, and tests
frontend/      Plain HTML, CSS, and JavaScript
terraform/     Planned AWS infrastructure and level3 course setup
 docs/         Research, implementation, API, devlog, and delivery documentation
CLAUDE.md      Context and working rules for future sessions
```

## Local setup

The following commands are **to be verified once the backend exists**:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
# Keep MOCK_AI=true for local UI work.
```

No API keys belong in this repository. Local AWS testing may use the developer's existing AWS CLI credentials, or `MOCK_AI=true` can provide canned responses once the backend supports it.

## Environment variables

| Variable           | Planned purpose                                | Example/default                               |
| ------------------ | ---------------------------------------------- | --------------------------------------------- |
| `BEDROCK_REGION`   | AWS Bedrock region                             | `eu-north-1`                                  |
| `BEDROCK_MODEL_ID` | Configurable Claude model or inference profile | `eu.anthropic.claude-haiku-4-5-20251001-v1:0` |
| `MOCK_AI`          | Use canned AI responses locally                | `true`                                        |
| `MAX_HINTS`        | Maximum hints per game                         | `2`                                           |
| `MAX_LIVES`        | Maximum lives per game                         | `6`                                           |
| `RATE_LIMIT`       | Per-IP request limit                           | `60 per minute`                               |
| `FLASK_DEBUG`      | Flask debug setting                            | `0`                                           |

## Deployment overview

Status: planned. Terraform and cloud-init are intended to provision an EC2 instance, install Nginx/Python/Gunicorn, configure a systemd service, and connect the app to Bedrock. See [terraform/README.md](terraform/README.md).

## Team and roles

- Chris: backend, AI integration, prompts, AWS deployment, and Phase 1-3 documentation.
- Gaby: frontend, UI, game mechanics, testing, Phase 2 and Phase 4 documentation, and conclusion.
- Shared: prompt testing, frontend/backend synchronization, AWS testing, video, and final push.

## Git workflow

- `main` is the stable branch.
- Use `chris/<topic>` and `gaby/<topic>` for focused work.
- Make small commits, pull before pushing, and review each other's pull requests.
- Never commit `.env`, credentials, API keys, or other secrets.

## Documentation index

- [Research](docs/research.md)
- [Implementation](docs/implementation.md)
- [API contract](docs/api_contract.md)
- [Devlog](docs/devlog.md)
- [Problems and solutions](docs/problems_solutions.md)
- [Finalization](docs/finalization.md)
- [Video script](docs/video_script.md)
- [Conclusion](docs/conclusion.md)

## Status checklist

- [ ] Repository skeleton reviewed
- [ ] Backend implemented
- [ ] Frontend implemented
- [ ] Prompt testing completed
- [ ] Automated tests completed
- [ ] Terraform and cloud-init completed
- [ ] AWS deployment completed
- [ ] Public link verified
- [ ] Documentation finalized
- [ ] English screen recording completed
- [ ] Final GitHub push completed

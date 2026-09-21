<!-- DRAFT: review and rewrite in your own words before submitting -->

# Phase 1: Research

## Goal and assignment requirements

The goal is to plan an English-language AI Hangman web application for the school GenAI assignment. The expected deliverables are a working public deployment, English documentation, an English screen recording of at least four minutes, and a GitHub repository. Generative AI must be central to the experience.

## Information sources used

- Assignment PDFs supplied for the school project requirements.
- AWS Bedrock documentation for model availability, pricing, and inference profiles.
- AWS CLI checks of available models.
- AWS Free Tier documentation.

## Technology choices

| Choice                              | Alternatives considered                 | Reason                                                           |
| ----------------------------------- | --------------------------------------- | ---------------------------------------------------------------- |
| Python + Flask                      | Django, FastAPI, Node.js                | Small backend surface and suitable for learning.                 |
| boto3 Bedrock Converse API          | Direct provider API, another AWS AI API | Fits the AWS deployment and structured message design.           |
| Plain HTML/CSS/JavaScript           | React, Vue, frontend build tools        | Keeps the project understandable and avoids a build step.        |
| EC2 + Nginx + Gunicorn              | App Runner, containers, static hosting  | Matches the level3 course setup and assignment deployment goals. |
| Terraform + cloud-init              | Manual setup                            | Documents repeatable infrastructure work.                        |
| One Claude model with three prompts | Multiple models, one combined prompt    | Keeps the AI design focused and makes each task testable.        |

## Cost planning

The account is a Free Plan account with credits. A monthly $20 budget alert is being created. Our own estimate is approximately `$0.002` per game, but this is only a planning estimate made before Bedrock access was confirmed, not a measured cost. A public IP and EC2 instance can also create costs even when AI usage is low.

Verified cost (2026-09-22): one full game (generate-word + hint + comment) used 408 tokens total on `eu.anthropic.claude-haiku-4-5-20251001-v1:0`, costing a small fraction of a cent.

## Work plan and milestones

1. Create and review the repository skeleton and documentation.
2. Implement the Flask API and server-side game state.
3. Add the three Bedrock prompts, validation, mock mode, and fallback data.
4. Build the mobile-first frontend against the API contract.
5. Test locally, deploy through Terraform/cloud-init, and verify the public link.
6. Finalize documentation and record the English video.

## Expected risks

The following are expected, not yet encountered:

- Model retirement or model ID changes.
- Repetitive AI-generated words.
- Cost abuse on a public IP.
- Bedrock access or account verification delays.
- Cloud-init debugging.

## Problems and solutions

Only real entries from [docs/devlog.md](devlog.md) belong here:

- Unexpected AWS cost from a running level1 EC2 instance and public IPv4 address.
- Billing access denied for the IAM user while the root account was needed.
- Bedrock access denied while the new account was being verified.

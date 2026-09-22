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

Status: deployed and verified

Terraform (`terraform/`) provisions one `t3.micro` EC2 instance (Amazon
Linux 2023) in the default VPC's public subnet, with a security group
allowing inbound HTTP (80, open) and SSH (22, restricted to `my_ip_cidr`)
and all outbound. No Elastic IP — the auto-assigned public IP is enough for
a short-lived grading deployment. An IAM role and instance profile are
attached to the instance with an inline policy scoped to
`bedrock:InvokeModel` and `bedrock:Converse` on the EU cross-region
inference profile and its underlying foundation-model ARNs in every EU
destination region that profile can route to from `eu-north-1` — no access
keys anywhere, matching CLAUDE.md's instance-profile requirement.

Cloud-init (`user_data.sh.tftpl`) installs Python 3, Nginx, and git; clones
the now-public repo over plain HTTPS; writes `.env` at the repo root
(`MOCK_AI=false`, `BEDROCK_REGION`/`BEDROCK_MODEL_ID` from Terraform
variables, `MAX_HINTS`/`MAX_LIVES`/`RATE_LIMIT` matching
`.env.example`'s defaults); builds `backend/.venv` and installs
`requirements.txt`; writes and starts a systemd service running `gunicorn
--workers 1 --threads 4 "app:create_app()"` from `backend/` (one worker
only — the in-memory game state depends on it); and configures Nginx as a
reverse proxy to `127.0.0.1:8000` for both `/` and `/api/`. A separate
`aws_budgets_budget` resource alerts `notification_email` at 50% and 80%
of a `$20`/month cap.

`terraform fmt` and `terraform validate` both pass. `terraform apply`
succeeded on 2026-09-22: 6 resources created (EC2 instance, security group,
IAM role, IAM role policy, IAM instance profile, AWS budget), 0 errors,
against account `117591992905` in `eu-north-1`.

Public URL: `http://51.20.142.127/` — confirmed reachable a few minutes
after apply completed, via `GET /api/health` returning `200 OK`. See
`terraform/README.md` for the exact `init`/`plan`/`apply`/`destroy`
commands and what to check after apply.

Full manual verification through the browser against the live public URL
(not just curl): played a complete game end to end (word `ERLANG`, loss),
against real Bedrock (`MOCK_AI=false` on the server, per the deployment
config). Confirmed via DevTools' Network tab: real AI latency (`generate-word`
~833ms, `hint` ~934ms-1.64s, `comment` ~1.67s, versus millisecond responses
in local mock testing), all 16 requests returned `200`, the secret word
only appeared after game over, the hint never leaked it, and the AI comment
was on-topic and well-written.

## Problems and solutions

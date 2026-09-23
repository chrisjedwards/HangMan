<!-- DRAFT: review and rewrite in your own words before submitting -->

# Development Log

## 2026-09-21: Unexpected AWS cost

- Problem: AWS cost was `$8.32` month-to-date on a Free Plan account, covered by credits.
- Cause: A level1 EC2 `t3.micro` instance named `level1-devops-jan-2026`, started on 2026-08-30, was still running along with its public IPv4 address. This was found through Billing > Cost breakdown and a CLI loop over all regions. `curl` was used to check what it served.
- Fix: Stopped it with `aws ec2 stop-instances`.
- Status: Still stopped, not terminated (verified with `aws ec2 describe-instances` on 2026-09-23); terminate/destroy it once confirmed unnecessary.

## 2026-09-21: Billing access denied

- Problem: IAM user `chris-admin` received "Access denied" in Billing.
- Cause: Billing access required the root account.
- Fix: Used the root account to view billing. The monthly `$20` budget alert now exists as the `aws_budgets_budget` resource created by `terraform apply` on 2026-09-22 (alerts at 50% and 80%).
- Status: Fixed.

## 2026-09-21: Bedrock account verification

- Problem: A Bedrock Converse call returned `AccessDeniedException`: "account is currently being verified".
- Cause: The Free Plan account was approximately two weeks old and still undergoing verification.
- Fix: Waited for verification to finish - see "2026-09-22: Bedrock Converse AccessDeniedException resolved" below.
- Status: Resolved 2026-09-22, see below.

## 2026-09-21: Unknown /api/* URLs returned 200 instead of a JSON 404

- Problem: Unknown `/api/*` URLs returned `200` with `index.html` instead of a JSON `404`.
- Cause: The dev server's catch-all route for the frontend matched `/api/*` before the error handler.
- Fix: Added an explicit `/api/<path>` route (all methods) that returns the contract's JSON 404; tested with GET and POST.
- Status: Fixed.

## 2026-09-22: Bedrock Converse AccessDeniedException resolved

- Problem: Bedrock Converse returned `AccessDeniedException`: "account is currently being verified".
- Cause: New AWS account verification, not yet complete when first tested (2026-09-21).
- Fix: Waited; retested the same command the next day and it succeeded with no further action needed.
- Status: Fixed.

## 2026-09-22: Old dev server kept answering after a restart attempt

- Problem: Restarting the dev server on the same port during manual testing left the old process still answering requests.
- Cause: A background job (`%1`) does not carry across separate tool invocations, so the old server was never actually killed.
- Fix: Kill by PID and verify with `ps`/`lsof` before starting a new instance.
- Status: Fixed.

## 2026-09-22: Verified .env loading from backend/

- Problem: Needed to confirm `.env` loads correctly when running from `backend/`, not just from the repo root.
- Cause: `load_dotenv()` default search behavior was assumed, not verified.
- Fix: Verified with a one-off command that `BEDROCK_REGION` resolves correctly from `backend/`; documented in README.
- Status: Fixed.

## 2026-09-22: pytest ran against the global Python install instead of .venv

- Problem: pytest ran against the global Python install instead of `.venv`, even after activating the virtual environment.
- Cause: zsh's command hash table still pointed at the previously used global pytest binary from earlier in the session.
- Fix: Recreated `.venv` from scratch, then ran `hash -r` to clear zsh's command cache; confirmed with `which pytest` and by checking the platform line in pytest's own output.
- Status: Fixed.

## 2026-09-22: Real Bedrock Converse calls failed with ResourceNotFoundException

- Problem: Real Bedrock Converse calls (generate-word, hint, comment) all failed with `ResourceNotFoundException`.
- Cause: "Model use case details have not been submitted for this account" - a separate AWS account setup step from the earlier verification issue.
- Fix: Submitted the Anthropic model use case form - see "2026-09-22: Bedrock ResourceNotFoundException resolved" below.
- Status: Resolved 2026-09-22, see below.

## 2026-09-22: Bedrock ResourceNotFoundException resolved

- Problem: Real Bedrock Converse calls failed with `ResourceNotFoundException` ("use case details have not been submitted").
- Cause: Anthropic requires first-time customers to submit use case details once per AWS account before invoking the model; the old "Model access" console page has been retired and this form is now under Model catalog instead.
- Fix: Submitted the use case form (Model catalog > Claude Haiku 4.5) describing the school project; access granted within a few minutes.
- Status: Fixed.

## 2026-09-22: Leftover dev server process still bound to the port (third occurrence)

- Problem: A leftover Flask/gunicorn dev server process from a previous session kept the port bound, so restarting the server risked the "old process still answering" bug (stale responses instead of fresh ones).
- Cause: Background processes started in one terminal/agent session don't always get cleanly killed before the next session starts a new server on the same port.
- Fix: Standard workaround now: check with `lsof -i :<port>` (or `ps`) before starting a new server instance, kill by PID if something is already listening, then start fresh.
- Status: Recurring - always check before starting the dev server.

## 2026-09-23: Code merged to main did not automatically appear on the live EC2 server

- Problem: Code merged to main on GitHub did not automatically appear on the live EC2 server.
- Cause: cloud-init (which clones the repo) only runs once, at first instance boot - it does not re-sync on later git pushes.
- Fix: SSH into the instance, `git pull` in `/opt/hangman`, then `sudo systemctl restart hangman` to pick up the new code.
- Status: Fixed - documented as the standard update procedure going forward.

<!-- DRAFT: review and rewrite in your own words before submitting -->

# Development Log

Use this entry format for real problems only:

```text
Date:
Problem:
Cause:
Fix:
Status:
```

## 2026-09-21: Unexpected AWS cost

- Problem: AWS cost was `$8.32` month-to-date on a Free Plan account, covered by credits.
- Cause: A level1 EC2 `t3.micro` instance named `level1-devops-jan-2026`, started on 2026-08-30, was still running along with its public IPv4 address. This was found through Billing > Cost breakdown and a CLI loop over all regions. `curl` was used to check what it served.
- Fix: Stopped it with `aws ec2 stop-instances`.
- Status: Stopped; terminate/destroy it once confirmed unnecessary.

## 2026-09-21: Billing access denied

- Problem: IAM user `chris-admin` received "Access denied" in Billing.
- Cause: Billing access required the root account.
- Fix: Used the root account to view billing and start creating a monthly `$20` budget alert.
- Status: In progress.

## 2026-09-21: Bedrock account verification

- Problem: A Bedrock Converse call returned `AccessDeniedException`: "account is currently being verified".
- Cause: The Free Plan account was approximately two weeks old and still undergoing verification.
- Fix: TBD. Retest the same call later; if it persists after two hours, email `aws-verification@amazon.com`.
- Status: OPEN.

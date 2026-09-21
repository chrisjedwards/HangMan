<!-- DRAFT: review and rewrite in your own words before submitting -->

# Terraform Deployment Plan

This directory will receive the Terraform code from the level3 course setup. No Terraform resources have been implemented in this scaffold.

## Planned resources

- One `t3.micro` EC2 instance.
- Security group allowing HTTP on port 80 and SSH on port 22.
- IAM role and instance profile allowing `bedrock:InvokeModel`.
- Cloud-init to install Nginx, Python, Gunicorn, and the systemd service.
- Nginx serving `frontend/` and proxying `/api/` to Gunicorn on `127.0.0.1`.
- A monthly budget alert.

The IAM policy must cover both the EU inference-profile ARN and the underlying foundation-model ARNs in the destination regions. The exact ARNs will be added when the deployment implementation is created.

The level3 course code will be copied into this directory before deployment work begins.

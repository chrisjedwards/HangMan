# Terraform Deployment

Status: applied and verified. Live public URL: http://51.20.142.127/

Deploys the already-tested Flask backend + frontend to one EC2 instance
(Amazon Linux 2023), behind Nginx, talking to real Bedrock through an IAM
instance profile - no access keys anywhere. See `docs/finalization.md` for
what this actually does and why.

## Files

| File                  | Contents                                                          |
| ---------------------- | ------------------------------------------------------------------ |
| `main.tf`              | EC2 instance, default VPC lookup, security group                  |
| `iam.tf`                | IAM role, inline Bedrock policy, instance profile                 |
| `budget.tf`             | `$20`/month AWS Budget with 50%/80% email alerts                   |
| `variables.tf`          | All input variables (two have no default - see below)             |
| `outputs.tf`            | Public IP and ready-to-use URL                                    |
| `user_data.sh.tftpl`    | Cloud-init script: clones the repo, builds the venv, starts gunicorn + Nginx |

## Prerequisites

- Terraform >= 1.5, AWS provider ~> 5.0 (both pinned in `main.tf`).
- AWS CLI credentials configured locally with permission to create EC2,
  IAM, and Budgets resources (`aws sts get-caller-identity` should work).
- An existing EC2 key pair in `eu-north-1` (or whichever region you pass as
  `bedrock_region`) to SSH in with - `aws ec2 describe-key-pairs --region
  eu-north-1` lists what you already have.
- Your current public IP in CIDR form for `my_ip_cidr`, e.g.
  `"$(curl -s ifconfig.me)/32"`.

## Commands

Run from `terraform/`:

```bash
terraform init
terraform fmt -check      # optional - confirms formatting only, no AWS calls
terraform validate        # syntax/type checks only, no AWS calls, no resources created

terraform plan \
  -var="my_ip_cidr=YOUR_IP/32" \
  -var="key_name=YOUR_KEY_PAIR_NAME" \
  -var="notification_email=you@example.com"

terraform apply \
  -var="my_ip_cidr=YOUR_IP/32" \
  -var="key_name=YOUR_KEY_PAIR_NAME" \
  -var="notification_email=you@example.com"
```

`terraform plan` shows exactly what will be created and its estimated
shape before anything is touched - review it before typing `yes` on apply.
`bedrock_region` and `bedrock_model_id` default to the values already
verified locally (`eu-north-1` /
`eu.anthropic.claude-haiku-4-5-20251001-v1:0`) - only pass `-var` for those
two if you want to deploy somewhere else.

## After `terraform apply`

`terraform apply` returns as soon as the EC2 instance is running - it does
**not** wait for cloud-init to finish installing packages, cloning the
repo, and starting services. That takes **5-10 minutes**. Until then,
`curl` against the app will fail or hang; that's expected, not a bug.

Check readiness:

```bash
curl http://$(terraform output -raw public_ip)/api/health
# {"status": "ok"} once cloud-init has finished
```

Or open the URL from `terraform output app_url` in a browser once that
curl succeeds.

## If it doesn't come up

SSH in and read the cloud-init log - every command the script ran, and
where it failed if it did, is in there (the script uses `set -x` on
purpose):

```bash
ssh -i /path/to/YOUR_KEY_PAIR_NAME.pem ec2-user@$(terraform output -raw public_ip)
sudo cat /var/log/cloud-init-output.log

# Once logged in, these are also useful:
sudo systemctl status hangman
sudo systemctl status nginx
sudo journalctl -u hangman -n 100 --no-pager
```

## Tearing down

This is a short-lived grading deployment, not a standing environment -
**destroy it once grading is done** so it doesn't keep costing money or
sitting open on a public IP:

```bash
terraform destroy \
  -var="my_ip_cidr=YOUR_IP/32" \
  -var="key_name=YOUR_KEY_PAIR_NAME" \
  -var="notification_email=you@example.com"
```

`terraform destroy` needs the same `-var` values as apply (Terraform has to
know what it's tearing down); if you saved them in a `terraform.tfvars`
file instead, drop the `-var` flags and destroy will read that file
automatically.

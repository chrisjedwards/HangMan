variable "instance_type" {
  description = "EC2 instance type. t3.micro is Free Tier eligible."
  type        = string
  default     = "t3.micro"
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR form (e.g. \"203.0.113.7/32\"), allowed to SSH in. Find yours with `curl -s ifconfig.me`. No default on purpose - never open SSH to 0.0.0.0/0."
  type        = string
}

variable "bedrock_region" {
  description = "AWS region to call Bedrock from (this is also the region the EC2 instance itself runs in - see main.tf). Must match a source region in the eu.* Bedrock geo inference profile."
  type        = string
  default     = "eu-north-1"
}

variable "bedrock_model_id" {
  description = "Bedrock inference profile ID passed to config.py's BEDROCK_MODEL_ID."
  type        = string
  default     = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "key_name" {
  description = "Name of an existing EC2 key pair to SSH in with. No default on purpose - must be a key pair that already exists in bedrock_region."
  type        = string
}

variable "notification_email" {
  description = "Email address for AWS Budget alerts (50% and 80% of $20/month). No default on purpose."
  type        = string
}

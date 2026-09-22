# Purpose: IAM role + instance profile for the EC2 instance, scoped to only
# the Bedrock calls the app actually makes (Converse; InvokeModel is
# included per spec even though services/ai.py only calls Converse today).
# No access keys anywhere - the app picks this up via the instance profile,
# same as boto3.client() does locally with AWS CLI credentials.
#
# Resource scope: the EU cross-region ("Geo: EU") inference profile for
# eu.anthropic.claude-haiku-4-5-20251001-v1:0 plus the underlying
# foundation-model ARNs in every destination region that profile can route
# to FROM eu-north-1 (our source region - var.bedrock_region's default).
# Per AWS's Bedrock model card for Claude Haiku 4.5, calling the EU geo
# profile from eu-north-1 can route to: eu-central-1, eu-north-1,
# eu-south-1, eu-south-2, eu-west-1, eu-west-3. (Two other EU regions,
# eu-west-2 and eu-central-2, appear as destinations only when the source
# region is eu-west-2/eu-central-2 themselves - not reachable from
# eu-north-1 - so they're deliberately left out here. If bedrock_region is
# ever changed away from eu-north-1, re-check the model card's Geo: EU
# table for that source region's actual destination list before applying.)

locals {
  bedrock_eu_destination_regions = [
    "eu-central-1",
    "eu-north-1",
    "eu-south-1",
    "eu-south-2",
    "eu-west-1",
    "eu-west-3",
  ]
  bedrock_base_model_id = "anthropic.claude-haiku-4-5-20251001-v1:0"
}

resource "aws_iam_role" "hangman" {
  name = "hangman-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "hangman_bedrock" {
  name = "hangman-bedrock-invoke"
  role = aws_iam_role.hangman.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeEuInferenceProfile"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:Converse",
        ]
        Resource = "arn:aws:bedrock:${var.bedrock_region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.bedrock_model_id}"
      },
      {
        Sid    = "InvokeUnderlyingFoundationModels"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:Converse",
        ]
        Resource = [
          for region in local.bedrock_eu_destination_regions :
          "arn:aws:bedrock:${region}::foundation-model/${local.bedrock_base_model_id}"
        ]
      },
    ]
  })
}

resource "aws_iam_instance_profile" "hangman" {
  name = "hangman-ec2-profile"
  role = aws_iam_role.hangman.name
}

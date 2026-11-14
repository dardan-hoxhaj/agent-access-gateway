# Minimal AWS sketch: ECR repository plus a GitHub OIDC role that can push to it.
# This is validate-only. It is not applied.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "github_org" {
  description = "GitHub org or user that owns the repo"
  type        = string
  default     = "dardan-hoxhaj"
}

variable "github_repo" {
  description = "Repository name"
  type        = string
  default     = "agent-access-gateway"
}

variable "aws_region" {
  description = "Region for the ECR repository"
  type        = string
  default     = "us-east-1"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_ecr_repository" "gateway" {
  name                 = "agent-access-gateway"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = {
    project = "agent-access-gateway"
  }
}

data "aws_iam_policy_document" "github_oidc_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role" "github_oidc" {
  name               = "agent-access-gateway-github-oidc"
  assume_role_policy = data.aws_iam_policy_document.github_oidc_assume.json
}

data "aws_iam_policy_document" "ecr_push" {
  statement {
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }
  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [aws_ecr_repository.gateway.arn]
  }
}

resource "aws_iam_role_policy" "ecr_push" {
  name   = "ecr-push"
  role   = aws_iam_role.github_oidc.id
  policy = data.aws_iam_policy_document.ecr_push.json
}

output "ecr_repository_url" {
  value = aws_ecr_repository.gateway.repository_url
}

output "github_oidc_role_arn" {
  value = aws_iam_role.github_oidc.arn
}

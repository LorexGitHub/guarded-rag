terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  endpoints {
    opensearch = "http://localhost:4566"
  }
}

resource "aws_opensearch_domain" "rag" {
  domain_name    = "rag"
  engine_version = "OpenSearch_2.19"
  cluster_config {
    instance_type  = "t3.small.search"
    instance_count = 1
  }
  # The aws provider waits a fixed 10 min before its first poll. A short create
  # timeout ends that wait and v5.x then checks once more. Needs provider v5.x; see ADR 0004.
  timeouts { create = "3m" }

  ebs_options {
    ebs_enabled = true
    volume_size = 10
  }
}

output "endpoint" { value = aws_opensearch_domain.rag.endpoint }

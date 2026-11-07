terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

variable "opensearch_url" {
  type        = string
  description = "OpenSearch endpoint reachable from Lambda containers"
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true
  endpoints {
    s3  = "http://localhost:4566"
    lambda = "http://localhost:4566"
    iam = "http://localhost:4566"
    sts = "http://localhost:4566"
    logs = "http://localhost:4566"
  }
}

resource "aws_s3_bucket" "docs" { bucket = "spike-docs" }

resource "aws_iam_role" "probe" {
  name = "spike-probe"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}

resource "aws_lambda_function" "probe" {
  function_name = "spike-probe"
  role          = aws_iam_role.probe.arn
  package_type  = "Image"
  image_uri     = "guarded-rag-spike-probe:latest"
  timeout       = 30
  environment {
    variables = {
      OLLAMA_URL     = "http://ollama:11434"
      OPENSEARCH_URL = var.opensearch_url
    }
  }
}

resource "aws_lambda_permission" "s3" {
  statement_id  = "AllowS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.probe.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.docs.arn
}

resource "aws_s3_bucket_notification" "docs" {
  bucket = aws_s3_bucket.docs.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.probe.arn
    events              = ["s3:ObjectCreated:*"]
  }
  depends_on = [aws_lambda_permission.s3]
}

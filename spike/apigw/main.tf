terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

variable "memory_size" {
  type    = number
  default = 1024
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  endpoints {
    lambda       = "http://localhost:4566"
    iam          = "http://localhost:4566"
    sts          = "http://localhost:4566"
    apigatewayv2 = "http://localhost:4566"
  }
}

resource "aws_iam_role" "fn" {
  name = "spike-presidio"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}

resource "aws_lambda_function" "redact" {
  function_name = "spike-redact"
  role          = aws_iam_role.fn.arn
  package_type  = "Image"
  image_uri     = "guarded-rag-presidio:latest"
  memory_size   = var.memory_size
  timeout       = 120
}

resource "aws_apigatewayv2_api" "api" {
  name          = "spike"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["http://localhost:5173"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type"]
  }
}

resource "aws_apigatewayv2_integration" "redact" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.redact.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "redact" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /redact"
  target    = "integrations/${aws_apigatewayv2_integration.redact.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowApiGw"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redact.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

output "api_id" { value = aws_apigatewayv2_api.api.id }

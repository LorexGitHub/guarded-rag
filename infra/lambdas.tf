# One image, two functions (ADR 0003): only the handler command and memory differ.
locals {
  lambda_env = {
    OPENSEARCH_URL = aws_opensearch_domain.rag.endpoint
    OLLAMA_URL     = var.ollama_url
    DOCS_BUCKET    = aws_s3_bucket.docs.bucket
  }
}

resource "aws_lambda_function" "ingest" {
  function_name = "guarded-rag-ingest"
  role          = aws_iam_role.ingest.arn
  package_type  = "Image"
  image_uri     = var.image_uri
  memory_size   = var.ingest_memory_size
  timeout       = 120
  image_config {
    command = ["ingest.handler"]
  }
  environment { variables = local.lambda_env }
}

resource "aws_lambda_function" "query" {
  function_name = "guarded-rag-query"
  role          = aws_iam_role.query.arn
  package_type  = "Image"
  image_uri     = var.image_uri
  memory_size   = var.query_memory_size
  timeout       = 60
  image_config {
    command = ["query.handler"]
  }
  environment { variables = local.lambda_env }
}

resource "aws_lambda_permission" "s3_ingest" {
  statement_id  = "AllowS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.docs.arn
}

resource "aws_lambda_permission" "apigw_query" {
  statement_id  = "AllowApiGw"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

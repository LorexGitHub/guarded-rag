# One image, two functions (ADR 0003): only the handler command and memory differ.
locals {
  route_functions = {
    query     = aws_lambda_function.query
    uploads   = aws_lambda_function.route["uploads"]
    documents = aws_lambda_function.route["documents"]
  }
  lambda_env = {
    OPENSEARCH_URL = aws_opensearch_domain.rag.endpoint
    OLLAMA_URL     = var.ollama_url
    UPLOAD_BUCKET  = aws_s3_bucket.docs.bucket
    ALLOWED_ORIGIN = var.cors_origin
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
    command = ["guarded_rag.handlers.ingest.handler"]
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
    command = ["guarded_rag.handlers.query.handler"]
  }
  environment { variables = local.lambda_env }
}

# ADR 0006 says one handler per route. /uploads and /documents are light (S3 only), so they get the default memory.
resource "aws_lambda_function" "route" {
  for_each      = toset(["uploads", "documents"])
  function_name = "guarded-rag-${each.key}"
  role          = aws_iam_role.query.arn
  package_type  = "Image"
  image_uri     = var.image_uri
  timeout       = 15
  image_config {
    command = ["guarded_rag.handlers.${each.key}.handler"]
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

resource "aws_lambda_permission" "apigw" {
  for_each      = local.route_functions
  statement_id  = "AllowApiGw"
  action        = "lambda:InvokeFunction"
  function_name = each.value.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

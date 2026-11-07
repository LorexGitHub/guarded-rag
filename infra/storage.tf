resource "aws_s3_bucket" "docs" {
  bucket = "guarded-rag-docs"
}

resource "aws_s3_bucket_cors_configuration" "docs" {
  bucket = aws_s3_bucket.docs.id
  cors_rule {
    allowed_origins = [var.cors_origin]
    allowed_methods = ["PUT"]
    allowed_headers = ["Content-Type"]
  }
}

# Ingest fires on uploads/ only; the status/ markers it writes must not retrigger it.
resource "aws_s3_bucket_notification" "docs" {
  bucket = aws_s3_bucket.docs.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.ingest.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
  }
  depends_on = [aws_lambda_permission.s3_ingest]
}

resource "aws_opensearch_domain" "rag" {
  domain_name    = "guarded-rag"
  engine_version = "OpenSearch_2.19"
  cluster_config {
    instance_type  = "t3.small.search"
    instance_count = 1
  }
  ebs_options {
    ebs_enabled = true
    volume_size = 10
  }
  # The provider waits a fixed 10 min before its first poll; a short timeout ends the wait (ADR 0004).
  timeouts { create = "3m" }
}

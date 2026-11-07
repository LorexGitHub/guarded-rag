resource "aws_apigatewayv2_api" "api" {
  name          = "guarded-rag"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = [var.cors_origin]
    allow_methods = ["POST", "GET"]
    allow_headers = ["content-type"]
  }
}

locals {
  routes = {
    query     = "POST /query"
    uploads   = "POST /uploads"
    documents = "GET /documents/{doc_id}"
  }
}

resource "aws_apigatewayv2_integration" "fn" {
  for_each               = local.routes
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = local.route_functions[each.key].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "routes" {
  for_each  = local.routes
  api_id    = aws_apigatewayv2_api.api.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.fn[each.key].id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

output "api_id" { value = aws_apigatewayv2_api.api.id }
output "opensearch_endpoint" { value = aws_opensearch_domain.rag.endpoint }

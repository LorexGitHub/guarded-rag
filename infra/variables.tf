variable "image_uri" {
  type        = string
  default     = "guarded-rag-lambda:latest"
  description = "Local image built by Compose (ADR 0003). Terraform only references it."
}

variable "cors_origin" {
  type        = string
  default     = "http://localhost:5173"
  description = "The one exact origin allowed by CORS: the S3 website origin of the UI (ADR 0006). Never *."
}

variable "ollama_url" {
  type    = string
  default = "http://ollama:11434"
}

variable "query_memory_size" {
  type    = number
  default = 512
}

variable "ingest_memory_size" {
  type    = number
  default = 1024
}

variable "s3_public_endpoint" {
  type        = string
  default     = "http://localhost:4566"
  description = "Host the browser uses to reach S3, put into presigned URLs. The Lambda's own endpoint is in-network."
}

# One image for every Lambda (ADR 0003). Build from the repo root:
#   docker build -f docker/lambda/Dockerfile -t guarded-rag-lambda:latest .
# Terraform picks the handler per function with image_config.command, for example
# ["guarded_rag.handlers.query.handler"].
FROM public.ecr.aws/lambda/python:3.12

COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /usr/local/bin/uv

# Dependencies and the spaCy model come first, so a code-only change rebuilds one layer.
# boto3 is already in the base image and is a dev dependency in pyproject.toml.
COPY pyproject.toml uv.lock /tmp/build/
RUN cd /tmp/build \
    && uv export --frozen --no-dev --no-emit-project -o requirements.txt \
    && uv pip install --system --no-cache -r requirements.txt \
    && rm -rf /tmp/build

COPY src/guarded_rag ${LAMBDA_TASK_ROOT}/guarded_rag

CMD ["guarded_rag.handlers.query.handler"]

FROM public.ecr.aws/lambda/python:3.12
RUN pip install --no-cache-dir presidio-analyzer presidio-anonymizer \
 && python -m spacy download en_core_web_md
COPY handler.py ${LAMBDA_TASK_ROOT}/
CMD ["handler.handler"]

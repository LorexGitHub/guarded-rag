"""The S3 calls the handlers make, behind one small interface (ADR 0005: S3 is not a seam)."""

import os
from typing import Protocol


class Objects(Protocol):
    def presign_put(self, key: str) -> str: ...

    def read(self, key: str) -> bytes | None: ...

    def write(self, key: str, data: bytes) -> None: ...


class S3Objects:
    """boto3 reads AWS_ENDPOINT_URL itself, which is how Floci is reached."""

    def __init__(self, bucket: str, public_endpoint: str | None = None):
        import boto3
        from botocore.config import Config

        self._bucket = bucket
        self._s3 = boto3.client("s3")
        # The browser cannot resolve Floci's in-network name, so presigned URLs may need
        # a different host from the one the Lambda uses.
        self._signer = boto3.client(
            "s3", endpoint_url=public_endpoint, config=Config(signature_version="s3v4")
        )

    def presign_put(self, key: str) -> str:
        return self._signer.generate_presigned_url(
            "put_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=900
        )

    def read(self, key: str) -> bytes | None:
        try:
            return self._s3.get_object(Bucket=self._bucket, Key=key)["Body"].read()
        except self._s3.exceptions.NoSuchKey:
            return None

    def write(self, key: str, data: bytes) -> None:
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType="application/json")


def build_objects() -> S3Objects:
    return S3Objects(os.environ["UPLOAD_BUCKET"], os.environ.get("S3_PUBLIC_ENDPOINT"))

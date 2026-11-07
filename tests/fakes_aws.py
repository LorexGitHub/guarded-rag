"""In-memory stand-in for the object store the handlers use."""


class FakeObjects:
    def __init__(self):
        self.blobs: dict[str, bytes] = {}

    def presign_put(self, key: str) -> str:
        return f"http://s3.test/{key}?signed"

    def read(self, key: str) -> bytes | None:
        return self.blobs.get(key)

    def write(self, key: str, data: bytes) -> None:
        self.blobs[key] = data

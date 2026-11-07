"""LLM over Bedrock converse (ADR 0001). On Floci it proxies to Ollama; on AWS it is Bedrock."""


class BedrockLLM:
    def __init__(self, client, model_id: str):
        self._client = client
        self._model_id = model_id

    def generate(self, system: str, user: str) -> str:
        response = self._client.converse(
            modelId=self._model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
        )
        return response["output"]["message"]["content"][0]["text"]

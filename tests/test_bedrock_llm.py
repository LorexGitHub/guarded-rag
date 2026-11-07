from guarded_rag.bedrock_llm import BedrockLLM


class FakeBedrock:
    def __init__(self):
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"role": "assistant", "content": [{"text": "the answer"}]}}}


def test_generate_sends_system_and_user_and_returns_text():
    client = FakeBedrock()
    llm = BedrockLLM(client, "some-model")
    assert llm.generate("be brief", "what is 2+2?") == "the answer"
    assert client.calls == [
        {
            "modelId": "some-model",
            "system": [{"text": "be brief"}],
            "messages": [{"role": "user", "content": [{"text": "what is 2+2?"}]}],
        }
    ]

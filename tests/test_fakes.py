import math

import pytest

from guarded_rag.seams import Chunk
from tests.contract import VectorStoreContract
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, RegexGuardrail


class TestFakeEmbedder:
    def test_vectors_have_dim_and_unit_length(self):
        e = FakeEmbedder(dim=8)
        [v] = e.embed_documents(["hello"])
        assert len(v) == e.dim == 8
        assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0)

    def test_same_text_same_vector_and_query_matches_document(self):
        e = FakeEmbedder()
        assert e.embed_query("a") == e.embed_documents(["a"])[0]

    def test_different_text_different_vector(self):
        e = FakeEmbedder()
        a, b = e.embed_documents(["a", "b"])
        assert a != b


class TestInMemoryVectorStore(VectorStoreContract):
    @pytest.fixture
    def store(self):
        return InMemoryVectorStore()


class TestFakeLLM:
    def test_returns_script_and_records_prompts(self):
        llm = FakeLLM("the answer")
        assert llm.generate("sys", "usr") == "the answer"
        assert llm.calls == [("sys", "usr")]


class TestRegexGuardrail:
    g = RegexGuardrail(names=["Alice Smith"])

    def test_text_without_pii_is_unchanged(self):
        r = self.g.redact("nothing here")
        assert r.text == "nothing here" and r.findings == []

    def test_redacts_email_phone_and_name(self):
        r = self.g.redact("Mail Alice Smith at a@b.com or 555-123-4567.")
        assert r.text == "Mail <PERSON_1> at <EMAIL_ADDRESS_1> or <PHONE_NUMBER_1>."
        assert {f.entity_type for f in r.findings} == {"PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"}

    def test_same_value_reuses_placeholder_and_new_value_increments(self):
        r = self.g.redact("a@b.com, a@b.com, c@d.com")
        assert r.text == "<EMAIL_ADDRESS_1>, <EMAIL_ADDRESS_1>, <EMAIL_ADDRESS_2>"

    def test_findings_hold_original_spans_and_no_raw_value(self):
        text = "x a@b.com"
        [f] = self.g.redact(text).findings
        assert (f.start, f.end) == (2, 9)
        assert text[f.start : f.end] == "a@b.com"
        assert "a@b.com" not in repr(f)


def test_chunk_is_frozen():
    c = Chunk("d", "s", 0, "t")
    with pytest.raises(AttributeError):
        c.text = "u"  # type: ignore[misc]

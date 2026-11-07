import pytest

from guarded_rag.config import CHUNK_CHARS
from guarded_rag.pipeline import REFUSAL, Deps, answer_question, chunk_text, ingest_document
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, RegexGuardrail


def make_deps(llm=None, guardrail=None):
    return Deps(
        guardrail=guardrail or RegexGuardrail(names=["Jane Doe"]),
        embedder=FakeEmbedder(),
        store=InMemoryVectorStore(),
        llm=llm or FakeLLM("fine"),
    )


def seed(deps, doc_id="handbook-md", text="Leave policy: 25 days."):
    return ingest_document(deps, doc_id, f"{doc_id}.md", text)


# chunking


def test_short_text_is_one_chunk():
    assert chunk_text("hello world") == ["hello world"]


def test_blank_text_has_no_chunks():
    assert chunk_text("  \n\n ") == []


def test_paragraphs_are_packed_up_to_the_limit():
    para = "a" * (CHUNK_CHARS // 2 - 5)
    chunks = chunk_text("\n\n".join([para] * 3))
    assert chunks == [para + "\n\n" + para, para]


def test_paragraphs_filling_the_limit_exactly_share_a_chunk():
    half = (CHUNK_CHARS - 2) // 2
    text = "a" * half + "\n\n" + "b" * half
    assert len(text) == CHUNK_CHARS
    assert chunk_text(text) == [text]


def test_words_filling_the_limit_exactly_stay_in_one_chunk():
    text = "x" * 400 + " " + "y" * (CHUNK_CHARS - 401)
    assert len(text) == CHUNK_CHARS
    assert chunk_text(text) == [text]


def test_oversized_paragraph_splits_on_word_boundaries():
    words = ["word"] * (CHUNK_CHARS)
    chunks = chunk_text(" ".join(words))
    assert len(chunks) > 1
    assert all(len(c) <= CHUNK_CHARS for c in chunks)
    assert " ".join(chunks).split() == words


def test_an_overlong_single_word_is_kept_whole():
    word = "x" * (CHUNK_CHARS + 10)
    assert chunk_text(word) == [word]


# ingest


def test_ingest_returns_chunk_count_and_makes_text_searchable():
    deps = make_deps()
    assert seed(deps) == 1
    hits = deps.store.search(deps.embedder.embed_query("Leave policy: 25 days."), 5, 0.99)
    assert [(h.chunk.doc_id, h.chunk.source, h.chunk.chunk_index) for h in hits] == [
        ("handbook-md", "handbook-md.md", 0)
    ]


def test_reingest_replaces_the_document():
    deps = make_deps()
    seed(deps, text="old text")
    seed(deps, text="new text")
    texts = [h.chunk.text for h in deps.store.search([1.0] * 8, 5, 0.0)]
    assert texts == ["new text"]


# query


def test_answer_is_generated_from_passed_chunks_with_sources():
    deps = make_deps(FakeLLM("25 days."))
    seed(deps)
    result = answer_question(deps, "Leave policy: 25 days.")
    assert (result.answer, result.refused) == ("25 days.", False)
    assert [(s.doc_id, s.source, s.chunk_index) for s in result.sources] == [
        ("handbook-md", "handbook-md.md", 0)
    ]
    assert [h.passed for h in result.trace.hits] == [True]
    (_, user) = deps.llm.calls[0]
    assert "Leave policy: 25 days." in user


def test_redacted_question_reaches_the_llm_but_retrieval_uses_the_original():
    deps = make_deps()
    original = "Where does Jane Doe work?"
    seed(deps, text=original)
    result = answer_question(deps, original)
    (system, user) = deps.llm.calls[0]
    assert "<PERSON_1>" in user and "Jane Doe" not in user.split("Question:")[-1]
    assert [f.placeholder for f in result.trace.findings_in] == ["<PERSON_1>"]
    assert result.trace.hits[0].passed  # exact original text matched, so the original was embedded


def test_answer_is_redacted_and_findings_out_reported():
    deps = make_deps(FakeLLM("Mail jane@corp.com"))
    seed(deps)
    result = answer_question(deps, "Leave policy: 25 days.")
    assert result.answer == "Mail <EMAIL_ADDRESS_1>"
    assert [f.entity_type for f in result.trace.findings_out] == ["EMAIL_ADDRESS"]


def test_trace_chunk_text_is_redacted_but_llm_context_is_raw():
    deps = make_deps()
    seed(deps, text="Call 555-123-4567 for leave.")
    result = answer_question(deps, "Call 555-123-4567 for leave.")
    assert result.trace.hits[0].chunk.text == "Call <PHONE_NUMBER_1> for leave."
    assert "555-123-4567" in deps.llm.calls[0][1]


def test_refusal_skips_the_llm_and_keeps_the_trace():
    deps = make_deps()
    seed(deps, text="Leave policy: 25 days.")
    result = answer_question(deps, "completely unrelated question zzz")
    assert (result.answer, result.refused, result.sources) == (REFUSAL, True, [])
    assert deps.llm.calls == []
    assert len(result.trace.hits) == 1 and not result.trace.hits[0].passed
    assert result.trace.findings_out == []


def test_empty_store_refuses():
    deps = make_deps()
    result = answer_question(deps, "anything")
    assert result.refused and result.trace.hits == []


class RaisingGuardrail:
    def redact(self, text):
        raise RuntimeError("presidio down")


def test_guardrail_failure_raises_and_nothing_reaches_the_llm():
    deps = make_deps(guardrail=RaisingGuardrail())
    with pytest.raises(RuntimeError):
        answer_question(deps, "hi")
    assert deps.llm.calls == []


class FailsOnAnswer:
    def __init__(self):
        self.inner = RegexGuardrail()
        self.calls = 0

    def redact(self, text):
        self.calls += 1
        if text == "raw answer":
            raise RuntimeError("boom")
        return self.inner.redact(text)


def test_answer_redaction_failure_returns_no_text():
    deps = make_deps(FakeLLM("raw answer"), guardrail=FailsOnAnswer())
    seed(deps)
    with pytest.raises(RuntimeError):
        answer_question(deps, "Leave policy: 25 days.")


def test_llm_failure_is_an_error_not_a_refusal():
    class Broken:
        def generate(self, system, user):
            raise ConnectionError

    deps = make_deps(Broken())
    seed(deps)
    with pytest.raises(ConnectionError):
        answer_question(deps, "Leave policy: 25 days.")

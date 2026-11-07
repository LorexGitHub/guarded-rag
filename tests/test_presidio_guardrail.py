import threading
import time

import pytest
from presidio_analyzer import RecognizerResult

from guarded_rag.guardrails.presidio import GuardrailError, PresidioGuardrail
from guarded_rag.guardrails.registry import load_registry


class ScriptedAnalyzer:
    """Returns spans for known values, so the placeholder logic runs without spaCy."""

    def __init__(self, values: dict[str, str]):
        self.values = values
        self.calls: list[dict] = []

    def analyze(self, text, language, entities, score_threshold):
        self.calls.append({"entities": entities, "score_threshold": score_threshold})
        found = []
        for value, kind in self.values.items():
            start = text.lower().find(value.lower())
            while start != -1:
                found.append(RecognizerResult(kind, start, start + len(value), 0.9))
                start = text.lower().find(value.lower(), start + 1)
        return found


class BrokenAnalyzer:
    def analyze(self, **_):
        raise RuntimeError("spaCy exploded")


class HangingAnalyzer:
    def __init__(self):
        self.release = threading.Event()

    def analyze(self, **_):
        self.release.wait(5)
        return []


def guardrail(values: dict[str, str], **kw) -> PresidioGuardrail:
    return PresidioGuardrail(ScriptedAnalyzer(values), load_registry(), **kw)


class TestPlaceholders:
    def test_replaces_a_value_with_a_typed_numbered_placeholder(self):
        r = guardrail({"Jane Doe": "PERSON"}).redact("Call Jane Doe now")
        assert r.text == "Call <PERSON_1> now"
        assert [(f.entity_type, f.placeholder, f.start, f.end) for f in r.findings] == [
            ("PERSON", "<PERSON_1>", 5, 13)
        ]

    def test_numbers_each_type_by_first_appearance(self):
        g = guardrail({"Ann": "PERSON", "Bob": "PERSON", "a@x.io": "EMAIL_ADDRESS"})
        r = g.redact("Bob, Ann, a@x.io, Bob")
        assert r.text == "<PERSON_1>, <PERSON_2>, <EMAIL_ADDRESS_1>, <PERSON_1>"

    def test_the_map_is_shared_across_question_and_answer(self):
        g = guardrail({"Ann": "PERSON", "Bob": "PERSON"})
        assert g.redact("Who is Ann?").text == "Who is <PERSON_1>?"
        assert g.redact("Bob works with Ann.").text == "<PERSON_2> works with <PERSON_1>."

    def test_case_and_whitespace_do_not_make_a_new_value(self):
        g = guardrail({"Jane  Doe": "PERSON", "JANE DOE": "PERSON"})
        assert g.redact("Jane  Doe and JANE DOE").text == "<PERSON_1> and <PERSON_1>"

    def test_a_new_request_starts_numbering_again(self):
        g = guardrail({"Ann": "PERSON", "Bob": "PERSON"})
        g.redact("Ann")
        assert g.for_request().redact("Bob").text == "<PERSON_1>"

    def test_text_without_pii_is_unchanged(self):
        r = guardrail({}).redact("Nothing here")
        assert (r.text, r.findings) == ("Nothing here", [])

    def test_overlapping_spans_keep_the_higher_score(self):
        class Overlap:
            def analyze(self, **_):
                return [
                    RecognizerResult("PERSON", 0, 7, 0.6),
                    RecognizerResult("EMPLOYEE_ID", 2, 11, 0.9),
                ]

        r = PresidioGuardrail(Overlap(), load_registry()).redact("xxEMP-12345 y")
        assert r.text == "xx<EMPLOYEE_ID_1> y"
        assert [f.entity_type for f in r.findings] == ["EMPLOYEE_ID"]

    @pytest.mark.parametrize(
        ("spans", "expected"),
        [
            # touching spans do not overlap, so both stay
            ([("PERSON", 0, 3, 0.9), ("EMAIL_ADDRESS", 3, 6, 0.9)], "<PERSON_1><EMAIL_ADDRESS_1>"),
            ([("PERSON", 0, 3, 0.8), ("EMAIL_ADDRESS", 3, 6, 0.9)], "<PERSON_1><EMAIL_ADDRESS_1>"),
            # the higher score wins even against a longer span
            ([("PERSON", 0, 6, 0.6), ("EMAIL_ADDRESS", 2, 4, 0.9)], "ab<EMAIL_ADDRESS_1>ef"),
            # equal scores: the longer span wins
            ([("PERSON", 0, 6, 0.9), ("EMAIL_ADDRESS", 5, 6, 0.9)], "<PERSON_1>"),
            # spans overlapping at the far edge are still one finding
            ([("PERSON", 0, 4, 0.9), ("EMAIL_ADDRESS", 3, 6, 0.8)], "<PERSON_1>ef"),
        ],
    )
    def test_overlap_rules(self, spans, expected):
        class Fixed:
            def analyze(self, **_):
                return [RecognizerResult(k, s, e, sc) for k, s, e, sc in spans]

        assert PresidioGuardrail(Fixed(), load_registry()).redact("abcdef").text == expected

    def test_only_registered_entities_are_requested_at_score_half(self):
        g = guardrail({})
        g.redact("x")
        call = g._analyzer.calls[0]
        assert sorted(call["entities"]) == [
            "EMAIL_ADDRESS",
            "EMPLOYEE_ID",
            "PERSON",
            "PHONE_NUMBER",
        ]
        assert call["score_threshold"] == 0.5

    def test_an_unregistered_entity_from_the_analyzer_is_ignored(self):
        r = guardrail({"Paris": "LOCATION"}).redact("Paris")
        assert (r.text, r.findings) == ("Paris", [])


class TestFailsClosed:
    def test_an_analyzer_error_raises_guardrail_error(self):
        with pytest.raises(GuardrailError):
            PresidioGuardrail(BrokenAnalyzer(), load_registry()).redact("Ann")

    def test_the_cause_is_kept_but_not_the_text(self):
        with pytest.raises(GuardrailError) as e:
            PresidioGuardrail(BrokenAnalyzer(), load_registry()).redact("secret Ann")
        assert isinstance(e.value.__cause__, RuntimeError)
        assert "secret" not in str(e.value)

    def test_a_timeout_raises_guardrail_error(self):
        slow = HangingAnalyzer()
        g = PresidioGuardrail(slow, load_registry(), timeout=0.05)
        started = time.monotonic()
        try:
            with pytest.raises(GuardrailError, match="timed out"):
                g.redact("Ann")
            assert time.monotonic() - started < 1
        finally:
            slow.release.set()


class TestRegistry:
    def test_employee_id_is_the_first_yaml_entry(self):
        reg = load_registry()
        assert reg.yaml_entities[0].entity_type == "EMPLOYEE_ID"
        assert reg.label("EMPLOYEE_ID") == "EMPLOYEE_ID"

    def test_a_new_entity_needs_only_a_yaml_entry(self, tmp_path):
        f = tmp_path / "r.yaml"
        f.write_text(
            "- entity_type: BADGE\n"
            "  label: BADGE\n"
            "  patterns:\n"
            "    - {name: badge, regex: 'B-\\d{3}', score: 0.8}\n"
        )
        reg = load_registry(f)
        assert "BADGE" in reg.entities
        assert reg.label("BADGE") == "BADGE"

    @pytest.mark.parametrize(
        "body", ["- entity_type: BADGE\n", "- entity_type: BADGE\n  patterns: []\n"]
    )
    def test_an_entry_without_patterns_is_rejected_at_load(self, tmp_path, body):
        f = tmp_path / "r.yaml"
        f.write_text(body)
        with pytest.raises(ValueError, match="BADGE"):
            load_registry(f)


@pytest.fixture(scope="module")
def real():
    from guarded_rag.guardrails.presidio import build_presidio_guardrail

    return build_presidio_guardrail()


@pytest.mark.slow
class TestRealPresidio:
    def test_detects_person(self, real):
        r = real.for_request().redact("Please email Jane Doe about the audit.")
        assert "Jane Doe" not in r.text
        assert any(f.entity_type == "PERSON" for f in r.findings)

    @pytest.mark.parametrize("phone", ["555-123-4567", "(555) 123-4567", "+1 555 123 4567"])
    def test_detects_phone_in_three_formats(self, real, phone):
        r = real.for_request().redact(f"Reach me on {phone} today.")
        assert phone not in r.text
        assert [f.entity_type for f in r.findings] == ["PHONE_NUMBER"]

    def test_detects_email(self, real):
        r = real.for_request().redact("Write to jane.doe@example.com please.")
        assert r.text == "Write to <EMAIL_ADDRESS_1> please."

    def test_detects_employee_id(self, real):
        r = real.for_request().redact("Her badge is EMP-48213.")
        assert r.text == "Her badge is <EMPLOYEE_ID_1>."

    def test_one_value_one_placeholder_across_texts(self, real):
        g = real.for_request()
        q = g.redact("Who is Jane Doe?")
        a = g.redact("Jane Doe is the CFO.")
        assert q.findings[0].placeholder == a.findings[0].placeholder == "<PERSON_1>"

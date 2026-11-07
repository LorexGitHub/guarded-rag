import re
from pathlib import Path

import pytest
import yaml

from corpus import generate

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
ENTITY_TYPES = {"PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "EMPLOYEE_ID"}


@pytest.fixture(scope="module")
def manifest():
    return yaml.safe_load((CORPUS / "ground_truth.yaml").read_text())


def doc_files():
    return sorted(p for p in CORPUS.iterdir() if p.suffix in {".md", ".txt"})


def words(path):
    return len(path.read_text().split())


def test_generator_is_deterministic_and_matches_committed_output():
    rendered = generate.render()
    assert rendered == generate.render()
    committed = {
        p.name: p.read_text() for p in CORPUS.iterdir() if p.is_file() and p.name != "generate.py"
    }
    assert committed == rendered


def test_main_writes_every_file_to_the_given_directory(tmp_path):
    generate.main(tmp_path)
    assert {p.name: p.read_text() for p in tmp_path.iterdir()} == generate.render()


def test_manifest_entries_have_the_adr_fields(manifest):
    assert manifest
    for entry in manifest:
        assert set(entry) == {"value", "entity_type", "doc", "normalized"}
        assert entry["entity_type"] in ENTITY_TYPES


def test_every_manifest_value_appears_in_its_doc(manifest):
    for entry in manifest:
        assert entry["value"] in (CORPUS / entry["doc"]).read_text(), entry


def test_normalized_forms(manifest):
    for entry in manifest:
        norm, value = entry["normalized"], entry["value"]
        if entry["entity_type"] == "PHONE_NUMBER":
            assert re.fullmatch(r"\d{10}", norm) and norm == re.sub(r"\D", "", value)[-10:]
        else:
            assert norm == " ".join(value.lower().split())


def test_corpus_shape():
    files = doc_files()
    assert len(files) == 14
    names = [p.name for p in files]
    assert sum(n.startswith("ticket-") for n in names) == 6
    assert "employee_directory.md" in names
    assert 4000 <= sum(words(p) for p in files) <= 8500


def test_policy_and_ticket_lengths():
    for path in doc_files():
        if path.name.startswith("ticket-"):
            assert 100 <= words(path) <= 250, path.name
        elif path.name.endswith("_policy.md") or path.name == "code_of_conduct.md":
            assert 300 <= words(path) <= 600, path.name


def test_filenames_contain_no_pii(manifest):
    pii_tokens = set()
    for entry in manifest:
        pii_tokens.update(entry["normalized"].replace("@", " ").replace(".", " ").split())
    pii_tokens = {t for t in pii_tokens if len(t) > 2 and t != "example" and t != "com"}
    for path in CORPUS.glob("*.*"):
        stem = path.stem.lower()
        assert not any(t in re.split(r"[^a-z0-9]+", stem) for t in pii_tokens), path.name


def values(manifest, entity_type):
    return {e["value"] for e in manifest if e["entity_type"] == entity_type}


def test_tricky_name_cases_are_seeded(manifest):
    people = values(manifest, "PERSON")
    assert {"Jane Doe", "Will Hunt", "Grace Park", "Mark Fields", "April Winter"} <= people
    emails = values(manifest, "EMAIL_ADDRESS")
    assert "will.hunt@example.com" in emails
    phones = values(manifest, "PHONE_NUMBER")
    formats = {
        "paren": r"\(\d{3}\) \d{3}-\d{4}",
        "dash": r"\d{3}-\d{3}-\d{4}",
        "plus": r"\+1 \d{3} \d{3} \d{4}",
    }
    for name, pattern in formats.items():
        assert any(re.fullmatch(pattern, p) for p in phones), name


def test_directory_lists_fifteen_employees_with_ids(manifest):
    ids = [e for e in manifest if e["entity_type"] == "EMPLOYEE_ID"]
    assert len(ids) == 15
    assert all(re.fullmatch(r"EMP-\d{5}", e["value"]) for e in ids)
    assert {e["doc"] for e in ids} == {"employee_directory.md"}

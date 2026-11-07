"""Entity registry (ADR 0009 decision 3): built-in Presidio entities plus YAML regex recognizers."""

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).with_name("recognizers.yaml")
BUILTIN_ENTITIES = ("PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS")


@dataclass(frozen=True)
class Pattern:
    name: str
    regex: str
    score: float


@dataclass(frozen=True)
class YamlEntity:
    entity_type: str
    label: str
    patterns: tuple[Pattern, ...]


@dataclass(frozen=True)
class Registry:
    yaml_entities: tuple[YamlEntity, ...]

    @property
    def entities(self) -> list[str]:
        return list(
            dict.fromkeys([*BUILTIN_ENTITIES, *(e.entity_type for e in self.yaml_entities)])
        )

    def label(self, entity_type: str) -> str:
        for e in self.yaml_entities:
            if e.entity_type == entity_type:
                return e.label
        return entity_type


def _parse_entity(raw: dict) -> YamlEntity:
    kind = raw.get("entity_type", "<missing entity_type>")
    raw_patterns = raw.get("patterns") or []
    patterns = tuple(Pattern(p["name"], p["regex"], float(p["score"])) for p in raw_patterns)
    if not patterns:
        raise ValueError(f"{kind}: needs at least one pattern")
    return YamlEntity(kind, raw.get("label", kind), patterns)


def load_registry(path: Path = DEFAULT_PATH) -> Registry:
    raw = yaml.safe_load(Path(path).read_text()) or []
    return Registry(tuple(_parse_entity(r) for r in raw))

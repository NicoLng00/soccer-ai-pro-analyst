"""Typed loader and validator for registry/sources.yaml and registry/variables.yaml.

The registry files are the source of truth for data sources and variables. This module
only validates them; loading into the database (`sap registry sync`) is built in phase 0.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Level = Literal["macro", "match", "micro"]
EntityKind = Literal["competition_season", "team", "person", "venue", "match", "match_team"]
Kind = Literal["raw", "derived", "model"]
DType = Literal["num", "cat", "bool", "json"]
TemporalKind = Literal["state", "event", "attribute"]
KnowableRule = Literal[
    "post_match", "kickoff_minus_60m", "publication", "announcement", "static", "pre_match"
]
BackfillPolicy = Literal["allowed", "rule", "excluded"]
Feasibility = Literal["collectable", "to_test", "approximable", "deferred"]
Status = Literal["experimental", "active", "retired"]
SourceKind = Literal["file", "api", "scrape", "rss", "manual", "derived", "agent"]
SourceStatus = Literal["active", "testing", "disabled"]

# Code prefixes that do not match entity_kind verbatim.
PREFIX_ALIASES: dict[str, EntityKind] = {"coach": "person"}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Source(_Strict):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    kind: SourceKind
    status: SourceStatus
    priority: int = Field(ge=1)
    terms_url: str
    license_note: str


class Variable(_Strict):
    code: str = Field(pattern=r"^[a-z_]+\.[a-z0-9_.]+$")
    level: Level
    entity_kind: EntityKind
    kind: Kind
    dtype: DType
    unit: str
    temporal_kind: TemporalKind
    knowable_rule: KnowableRule
    backfill_policy: BackfillPolicy
    feasibility: Feasibility
    status: Status
    version: int = Field(ge=1)
    sources: tuple[str, ...]
    description: str = Field(min_length=5)

    @model_validator(mode="after")
    def _check_consistency(self) -> Variable:
        prefix = self.code.split(".", 1)[0]
        expected = PREFIX_ALIASES.get(prefix, prefix)
        if expected != self.entity_kind:
            msg = f"{self.code}: prefix '{prefix}' does not match entity_kind '{self.entity_kind}'"
            raise ValueError(msg)
        if self.feasibility == "deferred" and self.status == "active":
            msg = f"{self.code}: a deferred variable cannot be active"
            raise ValueError(msg)
        if not self.sources and self.feasibility != "deferred":
            msg = f"{self.code}: only deferred variables may have no source"
            raise ValueError(msg)
        return self


class Registry(_Strict):
    sources: tuple[Source, ...]
    variables: tuple[Variable, ...]

    @model_validator(mode="after")
    def _check_references(self) -> Registry:
        for label, codes in (
            ("source", [s.code for s in self.sources]),
            ("variable", [v.code for v in self.variables]),
        ):
            dupes = [c for c, n in Counter(codes).items() if n > 1]
            if dupes:
                msg = f"duplicate {label} codes: {dupes}"
                raise ValueError(msg)
        known = {s.code for s in self.sources}
        for var in self.variables:
            missing = [s for s in var.sources if s not in known]
            if missing:
                msg = f"{var.code}: unknown sources {missing}"
                raise ValueError(msg)
        return self

    def by_code(self, code: str) -> Variable:
        for var in self.variables:
            if var.code == code:
                return var
        raise KeyError(code)


def _read_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"{path}: expected a mapping at top level"
        raise TypeError(msg)
    return data


def load_registry(registry_dir: Path) -> Registry:
    """Load and validate both registry files."""
    sources_doc = _read_yaml(registry_dir / "sources.yaml")
    variables_doc = _read_yaml(registry_dir / "variables.yaml")
    defaults = variables_doc.get("defaults", {})
    if not isinstance(defaults, dict):
        msg = "variables.yaml: 'defaults' must be a mapping"
        raise TypeError(msg)
    raw_vars = variables_doc.get("variables", [])
    if not isinstance(raw_vars, list):
        msg = "variables.yaml: 'variables' must be a list"
        raise TypeError(msg)
    variables = [{**defaults, **item} for item in raw_vars]
    return Registry.model_validate({"sources": sources_doc.get("sources", []), "variables": variables})

from pathlib import Path

import pytest

from soccer_analyst.registry import Registry, load_registry

REGISTRY_DIR = Path(__file__).resolve().parents[2] / "registry"


@pytest.fixture(scope="module")
def registry() -> Registry:
    return load_registry(REGISTRY_DIR)


def test_registry_loads(registry: Registry) -> None:
    assert len(registry.sources) >= 10
    assert len(registry.variables) >= 40


def test_every_level_is_covered(registry: Registry) -> None:
    assert {v.level for v in registry.variables} == {"macro", "match", "micro"}


def test_new_variables_start_experimental(registry: Registry) -> None:
    assert all(v.status == "experimental" for v in registry.variables)


def test_excluded_backfill_for_news_based_variables(registry: Registry) -> None:
    news_based = [v for v in registry.variables if "agent_news" in v.sources or "news_rss" in v.sources]
    assert news_based
    for var in news_based:
        if var.code == "match.crowd_restriction":
            continue
        assert var.backfill_policy == "excluded", var.code


def test_unknown_source_is_rejected(registry: Registry) -> None:
    data = registry.model_dump()
    data["variables"][0]["sources"] = ["does_not_exist"]
    with pytest.raises(ValueError, match="unknown sources"):
        Registry.model_validate(data)


def test_prefix_must_match_entity(registry: Registry) -> None:
    data = registry.model_dump()
    data["variables"][0]["code"] = "team.wrong_prefix"
    with pytest.raises(ValueError, match="does not match entity_kind"):
        Registry.model_validate(data)

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import yaml

from absencecritic.adapters.store.yaml_store import YamlStore
from absencecritic.domain.models import StoreKind
from absencecritic.paths import default_design_store_dir, default_store_dir, repo_root

ROOT = repo_root()


def test_design_failure_seed_loads_and_retrieves():
    store = YamlStore(default_design_store_dir())
    ids = {entry.id for entry in store.entries}
    assert "google-glass-explorer-2015" in ids
    assert "amazon-fire-phone-2015" in ids
    assert "windows-8-start-screen-primary" in ids
    glass = next(e for e in store.entries if e.id == "google-glass-explorer-2015")
    assert glass.kind.value == "design_failure"
    assert glass.blocker_status.value == "unknown"
    assert glass.source_url
    hits = store.retrieve(
        "Design consumer smart glasses that people will wear in public.",
        k=5,
    )
    assert any(entry.id == "google-glass-explorer-2015" for entry, _ in hits)


def test_chair_brief_does_not_retrieve_glass_or_the_fire_phone():
    store = YamlStore(default_design_store_dir())
    briefs = yaml.safe_load(
        (ROOT / "eval" / "generative" / "briefs.yaml").read_text(encoding="utf-8")
    )["briefs"]
    by_id = {item["id"]: item["brief"] for item in briefs}
    blocked = {
        "google-glass-explorer-2015",
        "amazon-fire-phone-2015",
        "consumer-device-hidden-battery-convention",
    }
    chair = [entry.id for entry, _score in store.retrieve(by_id["chair-apartment"], k=5)]
    assert not (blocked & set(chair))
    # The bottle brief says "no glass", so the Glass note can match on that word.
    # The Fire Phone and the battery note must not come along with it.
    bottle = [entry.id for entry, _score in store.retrieve(by_id["water-bottle"], k=5)]
    assert "amazon-fire-phone-2015" not in bottle
    assert "consumer-device-hidden-battery-convention" not in bottle


def test_shield_questions_never_retrieve_design_failures():
    shield = YamlStore(default_store_dir())
    assert all(entry.kind is StoreKind.evidence for entry in shield.entries)
    queries = yaml.safe_load(
        (ROOT / "eval" / "queries.yaml").read_text(encoding="utf-8")
    )["queries"]
    items = yaml.safe_load(
        (ROOT / "eval" / "benchmark" / "items.yaml").read_text(encoding="utf-8")
    )["items"]
    for row in list(queries) + list(items):
        hits = shield.retrieve(row["query"], k=5)
        assert all(entry.kind is StoreKind.evidence for entry, _score in hits), row["id"]


def test_bike_fixture_uses_the_frozen_brief():
    briefs = yaml.safe_load(
        (ROOT / "eval" / "generative" / "briefs.yaml").read_text(encoding="utf-8")
    )["briefs"]
    frozen = next(item["brief"] for item in briefs if item["id"] == "city-bike")
    recorded = yaml.safe_load(
        (ROOT / "eval" / "generative" / "fixtures.yaml").read_text(encoding="utf-8")
    )["responses"]
    assert any(item["query"] == frozen for item in recorded)


def test_generative_briefs_and_splits_are_frozen():
    import yaml

    briefs = yaml.safe_load(
        (ROOT / "eval" / "generative" / "briefs.yaml").read_text(encoding="utf-8")
    )["briefs"]
    splits = yaml.safe_load(
        (ROOT / "eval" / "generative" / "splits.yaml").read_text(encoding="utf-8")
    )
    ids = {item["id"] for item in briefs}
    assert len(briefs) >= 15
    assert "paper-airplane-control" in ids
    assert set(splits["train"]) | set(splits["heldout"]) == ids
    assert not (set(splits["train"]) & set(splits["heldout"]))
    for item in briefs:
        assert item["brief"].strip()
        assert item["known_designs"]
        # Store entry text must not be pasted into briefs.
        assert "google-glass-explorer-2015" not in item["brief"]
        assert "Explorer Edition" not in item["brief"]


def test_preregistration_exists_before_live_answers():
    text = (ROOT / "eval" / "generative" / "preregistration.md").read_text(
        encoding="utf-8"
    )
    assert "2026-11-25" in text
    assert "0.10" in text
    assert "invented-dead-design" in text

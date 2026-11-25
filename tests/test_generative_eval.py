# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from absencecritic.adapters.store.yaml_store import YamlStore
from absencecritic.paths import default_store_dir, repo_root

ROOT = repo_root()


def test_design_failure_seed_loads_and_retrieves():
    store = YamlStore(default_store_dir())
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

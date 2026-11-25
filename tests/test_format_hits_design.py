# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import yaml

from absencecritic.adapters.store.yaml_store import YamlStore


def test_format_hits_appends_design_fields_only_when_set(tmp_path: Path):
    entries = [
        {
            "id": "plain",
            "domain": "startups",
            "selection_process": "s",
            "survivor_pattern": "p",
            "non_survivor_evidence": "e",
            "confidence": 0.5,
            "provenance": "test",
        },
        {
            "id": "design-note",
            "domain": "product_design",
            "selection_process": "Only shipped products were reviewed",
            "survivor_pattern": "Shipped products",
            "non_survivor_evidence": "An external pack was abandoned",
            "confidence": 0.7,
            "provenance": "cited product page",
            "kind": "design_failure",
            "death_reason": "Weight of early packs",
            "blocker": "Battery density",
            "blocker_status": "expired",
            "event_date": "2012",
        },
    ]
    (tmp_path / "notes.yaml").write_text(
        yaml.safe_dump(entries, sort_keys=False), encoding="utf-8"
    )
    store = YamlStore(tmp_path)
    plain = next(e for e in store.entries if e.id == "plain")
    design = next(e for e in store.entries if e.id == "design-note")
    plain_text = store.format_hits([(plain, 0.5)])
    design_text = store.format_hits([(design, 0.9)])
    assert "kind:" not in plain_text
    assert "death_reason:" not in plain_text
    assert "kind: design_failure" in design_text
    assert "death_reason: Weight of early packs" in design_text
    assert "blocker_status: expired" in design_text
    assert "event_date: 2012" in design_text

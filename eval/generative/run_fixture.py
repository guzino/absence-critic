# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Fixture-only generative smoke: quiet control, ranked bike brief."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from absencecritic.adapters.llm.fixture import FixtureLLM
from absencecritic.adapters.store.yaml_store import YamlStore
from absencecritic.application.generative import run_generative
from absencecritic.paths import default_generative_fixture_path, default_store_dir


def main() -> int:
    provider = FixtureLLM(default_generative_fixture_path())
    store = YamlStore(default_store_dir())
    quiet = run_generative(
        "How do I fold a paper airplane?",
        provider=provider,
        store=store,
        use_store=False,
    )
    bike = run_generative(
        "Design a city bicycle for daily commuting.",
        provider=provider,
        store=store,
    )
    report = {
        "passed": 0,
        "failed": 0,
        "cases": [],
    }
    cases = [
        (
            "paper-airplane-quiet",
            quiet.ranked == [] and quiet.critique is not None
            and quiet.critique.survivorship_risk < 0.3,
        ),
        (
            "city-bike-ranked",
            bool(bike.ranked) and bike.ranked[0].id == "c1"
            and all(c.id != "c3" for c in bike.ranked),
        ),
    ]
    for name, ok in cases:
        report["cases"].append({"id": name, "ok": ok})
        if ok:
            report["passed"] += 1
        else:
            report["failed"] += 1
    print(json.dumps(report, indent=2))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

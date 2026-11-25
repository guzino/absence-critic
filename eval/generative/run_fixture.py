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
from absencecritic.paths import default_design_store_dir, default_generative_fixture_path


def _frozen_brief(brief_id: str) -> str:
    import yaml

    briefs = yaml.safe_load(
        (ROOT / "eval" / "generative" / "briefs.yaml").read_text(encoding="utf-8")
    )["briefs"]
    return next(item["brief"] for item in briefs if item["id"] == brief_id)


def main() -> int:
    provider = FixtureLLM(default_generative_fixture_path())
    store = YamlStore(default_design_store_dir())
    quiet = run_generative(
        _frozen_brief("paper-airplane-control"),
        provider=provider,
        store=store,
        use_store=False,
    )
    bike = run_generative(
        _frozen_brief("city-bike"),
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

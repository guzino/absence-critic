# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import importlib.util
from pathlib import Path

from absencecritic.adapters.llm.fixture import FixtureLLM

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    path = ROOT / "eval" / "record_fixtures.py"
    spec = importlib.util.spec_from_file_location("absencecritic_record_fixtures", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_record_fixtures_fixture_provider_roundtrips(tmp_path: Path):
    dest = tmp_path / "responses.yaml"
    queries = tmp_path / "queries.yaml"
    queries.write_text(
        ROOT.joinpath("eval", "queries.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    mod = _mod()
    assert (
        mod.main(
            [
                "--provider",
                "fixture",
                "--queries",
                str(ROOT / "eval" / "queries.yaml"),
                "--out",
                str(dest),
            ]
        )
        == 0
    )
    llm = FixtureLLM(dest)
    assert llm.generate(query="What is 2+2?").strip()
    critique = llm.critique(query="What is 2+2?", draft="4", store_hits="")
    assert "unchanged" in critique

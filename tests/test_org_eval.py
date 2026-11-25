# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

from answer_checks import leaks_pipeline  # noqa: E402


def _org_mod():
    spec = importlib.util.spec_from_file_location(
        "absencecritic_org_eval", ROOT / "eval" / "org_store" / "run.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fixture_org_eval_passes(capsys):
    assert _org_mod().main(["--provider", "fixture"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["arms"]["shield"]["right_entry_rate"] == 1.0
    assert payload["arm_deltas_meaningful"] is False


def test_every_question_retrieves_its_entry(tmp_path):
    mod = _org_mod()
    store = mod.build_store(tmp_path)
    for question in mod.load_questions():
        hits = [e.id for e, _ in store.retrieve(question["query"], k=5)]
        assert question["entry"] in hits, question["id"]


def test_custom_org_store_needs_a_live_provider(tmp_path, capsys):
    with pytest.raises(SystemExit):
        _org_mod().main(["--org-store", str(tmp_path)])
    assert "need --provider openai" in capsys.readouterr().err


def test_retrieval_only_runs_without_a_provider(tmp_path, capsys):
    team = tmp_path / "team"
    team.mkdir()
    mod = _org_mod()
    (team / "org.yaml").write_text(
        (mod.ORG_STORE / "org.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert mod.main(["--retrieval-only", "--org-store", str(team)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["retrieval_misses"] == []
    assert payload["questions"] == len(mod.load_questions())


def test_build_store_layers_a_team_directory(tmp_path):
    mod = _org_mod()
    team = tmp_path / "team"
    team.mkdir()
    (team / "notes.yaml").write_text(
        (mod.ORG_STORE / "org.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    work = tmp_path / "work"
    work.mkdir()
    store = mod.build_store(work, team, seed=False)
    assert [p.name for p in work.glob("*.yaml")] == ["team-notes.yaml"]
    hits = [e.id for e, _ in store.retrieve(mod.load_questions()[0]["query"], k=5)]
    assert mod.load_questions()[0]["entry"] in hits


def test_fictional_entries_stay_out_of_the_seed_store():
    org_ids = {
        e["id"]
        for e in yaml.safe_load(
            (ROOT / "eval" / "org_store" / "store" / "org.yaml").read_text(encoding="utf-8")
        )
    }
    seed_text = "\n".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "data" / "non_survivors").glob("*.yaml")
    )
    assert not any(i in seed_text for i in org_ids)
    assert all("fictional" in e["provenance"] for e in yaml.safe_load(
        (ROOT / "eval" / "org_store" / "store" / "org.yaml").read_text(encoding="utf-8")
    ))


def test_recorded_revisions_carry_the_fact_without_pipeline_talk():
    mod = _org_mod()
    recorded = {
        r["query"]: r["revision"]
        for r in yaml.safe_load(mod.FIXTURES_PATH.read_text(encoding="utf-8"))
    }
    for question in mod.load_questions():
        revision = recorded[question["query"]]
        assert re.search(question["fact"], revision, re.I), question["id"]
        assert not leaks_pipeline(revision), question["id"]

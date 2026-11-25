# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import json
from importlib import import_module
from pathlib import Path

import pytest

from absencecritic.adapters.llm.fixture import FixtureQueryNotFound
from absencecritic.cli import main


def test_cli_json_shielded(capsys):
    code = main(
        [
            "--provider",
            "fixture",
            "--json",
            "--show-critique",
            "What is 2+2?",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["shielded"] is True
    assert payload["critique"]["confidence_adjustment"] == "unchanged"


def test_cli_ingest(tmp_path, capsys):
    source = tmp_path / "new.yaml"
    store_dir = tmp_path / "store"
    store_dir.mkdir()
    (store_dir / "seed.yaml").write_text(
        """
- id: seed
  domain: physics
  selection_process: none
  survivor_pattern: constants
  non_survivor_evidence: n/a
  confidence: 0.1
  provenance: test
""",
        encoding="utf-8",
    )
    source.write_text(
        """
- id: file-drawer-note
  domain: scientific_literature
  selection_process: journals prefer positive results
  survivor_pattern: published significant findings
  non_survivor_evidence: unpublished nulls are missing from the visible literature
  confidence: 0.5
  provenance: Author prior, low confidence
""",
        encoding="utf-8",
    )
    code = main(["ingest", str(source), "--store", str(store_dir)])
    assert code == 0
    assert "file-drawer-note" in capsys.readouterr().out
    assert (store_dir / "ingested.yaml").exists()


def test_cli_ingest_catalog(tmp_path, capsys):
    fixture = Path(__file__).resolve().parent / "fixtures" / "catalog.yaml"
    store_dir = tmp_path / "store"
    store_dir.mkdir()
    code = main(["ingest", "--catalog", str(fixture), "--store", str(store_dir)])
    assert code == 0
    out = capsys.readouterr().out
    assert "catalog-bls-startup-survival" in out
    assert (store_dir / "ingested.yaml").exists()


def test_cli_local_critic_json(monkeypatch, capsys):
    from absencecritic.adapters.llm.openai_compat import OpenAICompat

    payload = json.dumps(
        {
            "selection_filter": "Arithmetic identity; not filtered by publication or platform survival.",
            "visible_damage": [],
            "empty_regions": [],
            "non_survivors": [],
            "unknown_lethality": [],
            "survivorship_risk": 0.0,
            "confidence_adjustment": "unchanged",
            "caveats": [],
            "missing_categories": [],
            "suggested_queries": [],
        }
    )
    monkeypatch.setattr(OpenAICompat, "_chat", lambda *a, **k: payload)
    code = main(
        [
            "--provider",
            "fixture",
            "--critic",
            "local",
            "--json",
            "What is 2+2?",
        ]
    )
    assert code == 0
    body = json.loads(capsys.readouterr().out)
    assert body["critique"]["confidence_adjustment"] == "unchanged"
    assert body["draft"]


def test_cli_judge_skips_generate(tmp_path, capsys):
    draft = tmp_path / "draft.txt"
    draft.write_text("2 + 2 = 4.", encoding="utf-8")
    code = main(
        [
            "--provider",
            "fixture",
            "--judge",
            "--draft-file",
            str(draft),
            "--json",
            "What is 2+2?",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["draft"] == "2 + 2 = 4."
    assert payload["final"] == ""
    assert payload["critique"]["confidence_adjustment"] == "unchanged"


def test_cli_no_shield(capsys):
    code = main(["--provider", "fixture", "--no-shield", "--json", "What is 2+2?"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["shielded"] is False
    assert payload["critique"] is None


def test_cli_unknown_fixture_query_is_a_short_error(capsys):
    code = main(["--provider", "fixture", "An unrecorded regression-test question"])
    out, err = capsys.readouterr()
    assert code == 1
    assert not out
    assert "recorded demo questions" in err
    assert "What is 2+2?" in err
    assert "--provider openai" in err
    assert "Traceback" not in err
    assert "An unrecorded regression-test question" not in err


def test_cli_debug_preserves_unknown_fixture_exception():
    with pytest.raises(FixtureQueryNotFound):
        main(["--provider", "fixture", "--debug", "An unrecorded regression-test question"])


def test_cli_live_provider_without_key_is_a_short_error(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cli_module = import_module("absencecritic.adapters.cli.main")
    monkeypatch.setattr(cli_module, "load_repo_env", lambda: None)

    assert main(["--provider", "openai", "What is 2+2?"]) == 1
    out, err = capsys.readouterr()
    assert not out
    assert "Set OPENAI_API_KEY" in err
    assert "Traceback" not in err

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "eval" / "gold"


def _export_mod():
    path = ROOT / "eval" / "export_gold.py"
    spec = importlib.util.spec_from_file_location("absencecritic_export_gold", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gold_records_validate_and_match_committed_jsonl(tmp_path: Path):
    mod = _export_mod()
    rows = mod.gold_records()
    assert len(rows) >= 15
    kinds = {row["kind"] for row in rows}
    assert "biased" in kinds
    assert "control" in kinds
    assert all(row["id"] for row in rows)
    assert all(row["provenance"] == "eval/fixtures/responses.yaml" for row in rows)
    dest = tmp_path / "critiques.jsonl"
    written = mod.write_gold(dest)
    for name in ("critiques.jsonl", "train.jsonl", "heldout.jsonl"):
        assert (tmp_path / name).read_text(encoding="utf-8") == (
            GOLD / name
        ).read_text(encoding="utf-8")
    assert written == dest


def test_train_and_heldout_are_disjoint_and_cover_gold():
    mod = _export_mod()
    train_ids, heldout_ids = mod.load_splits()
    overlap = set(train_ids) & set(heldout_ids)
    assert not overlap
    gold_ids = {row["id"] for row in mod.gold_records()}
    assert set(train_ids) | set(heldout_ids) == gold_ids
    heldout_rows = [row for row in mod.gold_records() if row["id"] in set(heldout_ids)]
    heldout_kinds = {row["kind"] for row in heldout_rows}
    assert "biased" in heldout_kinds
    assert "control" in heldout_kinds


def _control_critique() -> dict:
    return {
        "selection_filter": "Arithmetic identity; not filtered by publication or platform survival.",
        "visible_damage": [],
        "empty_regions": [],
        "non_survivors": [],
        "unknown_lethality": [],
        "survivorship_risk": 0.0,
        "confidence_adjustment": "unchanged",
        "caveats": ["Human overlay test only."],
        "missing_categories": [],
        "suggested_queries": [],
    }


def test_overlay_unknown_id_fails():
    mod = _export_mod()
    rows = mod.gold_records()
    with pytest.raises(ValueError, match="not in gold"):
        mod.apply_overlay(rows, {"not-a-query": {"critique": _control_critique()}})


def test_overlay_missing_provenance_fails(tmp_path: Path):
    mod = _export_mod()
    bad = tmp_path / "overlay.yaml"
    bad.write_text(
        yaml.safe_dump(
            {
                "overlays": [
                    {
                        "id": "two-plus-two",
                        "editor": "tester",
                        "date": "2026-11-24",
                        "critique": _control_critique(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing"):
        mod.load_overlays(bad)


def test_overlay_wins_on_train_export_not_fixture_jsonl(tmp_path: Path):
    mod = _export_mod()
    overlay = tmp_path / "overlay.yaml"
    overlay.write_text(
        yaml.safe_dump(
            {
                "overlays": [
                    {
                        "id": "two-plus-two",
                        "editor": "tester",
                        "date": "2026-11-24",
                        "reason": "control over-flagged",
                        "critique": _control_critique(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    dest = tmp_path / "out" / "critiques.jsonl"
    mod.write_gold(dest, overlay_path=overlay)
    union = [
        json.loads(line)
        for line in dest.read_text(encoding="utf-8").splitlines()
        if line
    ]
    train = [
        json.loads(line)
        for line in (dest.parent / "train.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    fixture_row = next(row for row in union if row["id"] == "two-plus-two")
    train_row = next(row for row in train if row["id"] == "two-plus-two")
    assert fixture_row["critique"]["caveats"] == []
    assert "overlay_editor" not in fixture_row
    assert train_row["critique"]["caveats"] == ["Human overlay test only."]
    assert train_row["overlay_editor"] == "tester"
    assert train_row["overlay_reason"] == "control over-flagged"


def test_export_gold_help_does_not_write(tmp_path: Path, monkeypatch):
    mod = _export_mod()
    monkeypatch.chdir(tmp_path)
    before = {path.name: path.read_text(encoding="utf-8") for path in GOLD.glob("*.jsonl")}
    with pytest.raises(SystemExit) as exited:
        mod.main(["--help"])
    assert exited.value.code == 0
    after = {path.name: path.read_text(encoding="utf-8") for path in GOLD.glob("*.jsonl")}
    assert after == before


def test_export_gold_check_passes_on_committed_files():
    mod = _export_mod()
    assert mod.main(["--check"]) == 0


def test_export_gold_overlay_flag_checks_without_writing(tmp_path: Path, capsys):
    mod = _export_mod()
    overlay = tmp_path / "draft-overlay.yaml"
    overlay.write_text(
        yaml.safe_dump(
            {
                "overlays": [
                    {
                        "id": "two-plus-two",
                        "editor": "tester",
                        "date": "2026-11-24",
                        "reason": "trying a draft overlay",
                        "critique": _control_critique(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    before = {path.name: path.read_text(encoding="utf-8") for path in GOLD.glob("*.jsonl")}
    assert mod.main(["--check", "--overlay", str(overlay)]) == 1
    assert "train.jsonl" in capsys.readouterr().out
    after = {path.name: path.read_text(encoding="utf-8") for path in GOLD.glob("*.jsonl")}
    assert after == before

    dest = tmp_path / "out" / "critiques.jsonl"
    assert mod.main(["--out", str(dest), "--overlay", str(overlay)]) == 0
    train = (dest.parent / "train.jsonl").read_text(encoding="utf-8")
    assert "trying a draft overlay" in train


def test_export_gold_overlay_flag_rejects_missing_file(tmp_path: Path):
    with pytest.raises(SystemExit):
        _export_mod().main(["--check", "--overlay", str(tmp_path / "nope.yaml")])


def test_overlapping_splits_fail(tmp_path: Path):
    mod = _export_mod()
    bad = tmp_path / "splits.yaml"
    bad.write_text(
        yaml.safe_dump({"train": ["startup-launch"], "heldout": ["startup-launch"]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="both train and heldout"):
        mod.load_splits(bad)

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from absencecritic import paths

ROOT = Path(__file__).resolve().parents[1]


def test_checkout_paths_win_when_present(monkeypatch):
    monkeypatch.delenv("ABSENCECRITIC_STORE", raising=False)
    monkeypatch.delenv("ABSENCECRITIC_DESIGN_STORE", raising=False)
    monkeypatch.delenv("ABSENCECRITIC_FIXTURES", raising=False)
    assert paths.default_store_dir() == ROOT / "data" / "non_survivors"
    assert paths.default_design_store_dir() == ROOT / "data" / "design_failures"
    assert paths.default_fixture_path() == ROOT / "eval" / "fixtures" / "responses.yaml"


def test_installed_package_falls_back_to_packaged_data(monkeypatch, tmp_path):
    monkeypatch.delenv("ABSENCECRITIC_STORE", raising=False)
    monkeypatch.delenv("ABSENCECRITIC_DESIGN_STORE", raising=False)
    monkeypatch.delenv("ABSENCECRITIC_FIXTURES", raising=False)
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)
    assert paths.default_store_dir() == paths.PACKAGED_DATA / "non_survivors"
    assert paths.default_design_store_dir() == paths.PACKAGED_DATA / "design_failures"
    assert paths.default_fixture_path() == paths.PACKAGED_DATA / "fixtures" / "responses.yaml"


def test_env_overrides_everything(monkeypatch, tmp_path):
    monkeypatch.setenv("ABSENCECRITIC_STORE", str(tmp_path / "org"))
    monkeypatch.setenv("ABSENCECRITIC_FIXTURES", str(tmp_path / "f.yaml"))
    assert paths.default_store_dir() == tmp_path / "org"
    assert paths.default_fixture_path() == tmp_path / "f.yaml"


def test_wheel_force_include_matches_packaged_paths():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert (
        '"data/non_survivors/entries.yaml" = "absencecritic/_data/non_survivors/entries.yaml"'
        in text
    )
    assert (
        '"eval/fixtures/responses.yaml" = "absencecritic/_data/fixtures/responses.yaml"'
        in text
    )

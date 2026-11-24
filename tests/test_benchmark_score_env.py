# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path


def _load_score_module():
    score_path = Path(__file__).resolve().parents[1] / "eval" / "benchmark" / "score.py"
    spec = importlib.util.spec_from_file_location("benchmark_score", score_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_score_main_loads_repo_env_before_openai_judge(tmp_path, monkeypatch):
    score_mod = _load_score_module()
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-test-from-dotenv\n", encoding="utf-8")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    real_load_repo_env = score_mod.load_repo_env
    monkeypatch.setattr(score_mod, "load_repo_env", lambda: real_load_repo_env(env_file))

    items_path = tmp_path / "items.yaml"
    items_path.write_text(
        "items:\n"
        "  - id: env-1\n"
        "    kind: control\n"
        "    domain: math\n"
        "    annotator: independent\n"
        "    query: 'What is 2+2?'\n"
        "    labels:\n"
        "      should_caveate: false\n"
        "      should_not_abstain: true\n"
        "      must_mention_missing_data: false\n",
        encoding="utf-8",
    )
    answers_path = tmp_path / "answers.jsonl"
    answers_path.write_text(
        json.dumps({"id": "env-1", "answer": "4."}) + "\n",
        encoding="utf-8",
    )

    seen_keys: list[str | None] = []

    def fake_judge(item, answer, *, abstained=None, kind="heuristic", draft=None):
        seen_keys.append(os.environ.get("OPENAI_API_KEY"))
        return {"kind": kind, "pass": True}

    monkeypatch.setattr(score_mod, "judge_answer", fake_judge)

    rc = score_mod.main(
        ["--items", str(items_path), "--answers", str(answers_path), "--judge", "openai"]
    )
    assert rc == 0
    assert seen_keys == ["sk-test-from-dotenv"]

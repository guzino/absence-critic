# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _eval_mod():
    eval_path = ROOT / "eval" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("absencecritic_eval", eval_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fixture_eval_passes(capsys):
    assert _eval_mod().main(["--provider", "fixture"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] == payload["total"]
    case = next(row for row in payload["cases"] if row["id"] == "startup-launch")
    assert case["shared_draft"] is True
    drafts = {arm["draft"] for arm in case["arms"].values()}
    assert len(drafts) == 1
    assert set(case["arms"]) == {"baseline", "generic", "critic_only", "shield"}
    assert payload["arm_deltas_meaningful"] is False
    assert "not a result" in payload["note"]


def test_generic_arm_sends_fixed_caution_and_no_store():
    mod = _eval_mod()
    seen: list[str] = []

    class Gen:
        def revise(self, *, query: str, draft: str, critique_json: str) -> str:
            seen.append(critique_json)
            return draft + " Failures may be missing."

    from eval_arms import GENERIC_CAUTION

    result = mod.generic_arm("q", "draft", generator=Gen())
    assert result.retrieved_ids == []
    assert result.critique is None
    sent = json.loads(seen[0])
    assert sent == GENERIC_CAUTION.model_dump(mode="json")
    assert sent["non_survivors"] == []


def test_critic_only_arm_is_store_free(capsys):
    assert _eval_mod().main(["--provider", "fixture"]) == 0
    payload = json.loads(capsys.readouterr().out)
    for case in payload["cases"]:
        assert case["arms"]["critic_only"]["retrieved_ids"] == [], case["id"]


def test_fixture_eval_samples_reports_arm_spread(capsys):
    assert _eval_mod().main(["--provider", "fixture", "--samples", "2"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["samples"] == 2
    assert payload["arms"]["shield"]["spread"] == 0.0
    assert payload["arms"]["shield"]["mean"] == 1.0


def test_eval_records_error_and_continues(tmp_path, capsys):
    queries = tmp_path / "queries.yaml"
    queries.write_text(
        """
queries:
  - id: startup-launch
    kind: biased
    query: What works for launching a startup?
  - id: two-plus-two
    kind: control
    query: What is 2+2?
  - id: ml-tricks
    kind: biased
    query: Which ML tricks always improve accuracy?
""",
        encoding="utf-8",
    )
    mod = _eval_mod()
    real_run = mod.run

    def boom(query, **kwargs):
        if "2+2" in query:
            raise ValueError("invalid critique json")
        return real_run(query, **kwargs)

    mod.run = boom
    jsonl = tmp_path / "cases.jsonl"
    code = mod.main(
        [
            "--provider",
            "fixture",
            "--queries",
            str(queries),
            "--jsonl",
            str(jsonl),
        ]
    )
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == 3
    assert payload["errored"] == 1
    assert payload["passed"] == 2
    by_id = {row["id"]: row for row in payload["cases"]}
    assert "error" in by_id["two-plus-two"]
    assert "ValueError" in by_id["two-plus-two"]["error"]
    assert by_id["startup-launch"]["pass"] is True
    assert by_id["ml-tricks"]["pass"] is True
    lines = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    assert [row["id"] for row in lines] == [
        "startup-launch",
        "two-plus-two",
        "ml-tricks",
    ]


def test_eval_error_row_keeps_raw_critic_reply(tmp_path, capsys):
    queries = tmp_path / "queries.yaml"
    queries.write_text(
        "queries:\n  - id: two-plus-two\n    kind: control\n    query: What is 2+2?\n",
        encoding="utf-8",
    )
    mod = _eval_mod()
    real = mod.FixtureLLM(ROOT / "eval" / "fixtures" / "responses.yaml")

    class Garbled:
        def generate(self, *, query):
            return real.generate(query=query)

        def critique(self, *, query, draft, store_hits):
            return "Sure! Here is my critique: risk is high"

        def revise(self, *, query, draft, critique_json):
            return real.revise(query=query, draft=draft, critique_json=critique_json)

    mod.FixtureLLM = lambda path: Garbled()
    assert mod.main(["--provider", "fixture", "--queries", str(queries)]) == 1
    row = json.loads(capsys.readouterr().out)["cases"][0]
    assert "CritiqueParseError" in row["error"]
    assert row["raw_critique"] == "Sure! Here is my critique: risk is high"

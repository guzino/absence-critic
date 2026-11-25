# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
import os
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

PASSING_UNKNOWN = (
    "Shortlist the decade stayers. They are the winners; the unknown cases already left."
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _score_mod():
    return _load("absencecritic_benchmark_score", ROOT / "eval" / "benchmark" / "score.py")


def _judge_mod():
    return _load("absencecritic_benchmark_judge", ROOT / "eval" / "benchmark" / "judge.py")


def _run_mod():
    return _load("absencecritic_benchmark_run", ROOT / "eval" / "benchmark" / "run.py")


def _query_ids() -> set[str]:
    queries = yaml.safe_load((ROOT / "eval" / "queries.yaml").read_text(encoding="utf-8"))
    splits = yaml.safe_load((ROOT / "eval" / "gold" / "splits.yaml").read_text(encoding="utf-8"))
    ids = {item["id"] for item in queries["queries"]}
    ids.update(splits["train"])
    ids.update(splits["heldout"])
    return ids


def test_benchmark_ids_disjoint_from_gold_and_fixture_eval():
    mod = _score_mod()
    items = mod.load_items()
    bench_ids = {item["id"] for item in items}
    overlap = bench_ids & _query_ids()
    assert not overlap
    kinds = {item["kind"] for item in items}
    assert "biased" in kinds
    assert "control" in kinds


def _non_benchmark_texts():
    for root in (ROOT / "src", ROOT / "tests"):
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".yaml"}:
                yield path
    eval_dir = ROOT / "eval"
    yield eval_dir / "queries.yaml"
    yield eval_dir / "queries_paraphrase.yaml"
    yield eval_dir / "fixtures" / "responses.yaml"
    yield eval_dir / "gold" / "overlay.yaml"
    yield from (eval_dir / "gold").glob("*.jsonl")


def test_benchmark_queries_and_ids_are_absent_outside_the_benchmark():
    items = _score_mod().load_items()
    texts = {path: path.read_text(encoding="utf-8") for path in _non_benchmark_texts()}
    for item in items:
        for path, text in texts.items():
            assert item["query"] not in text, f"{item['id']} query copied into {path}"
            if path.parent.name != "tests":
                assert item["id"] not in text, f"{item['id']} id used in {path}"


def test_benchmark_fixtures_only_record_current_items():
    items = _score_mod().load_items()
    fixtures = yaml.safe_load(
        (ROOT / "eval" / "benchmark" / "fixtures.yaml").read_text(encoding="utf-8")
    )
    recorded = {row["query"].strip() for row in fixtures}
    assert recorded <= {item["query"].strip() for item in items}
    kinds = {item["kind"] for item in items if item["query"].strip() in recorded}
    assert kinds == {"biased", "control"}


def test_benchmark_size_and_spread():
    stats = _score_mod().item_stats(_score_mod().load_items())
    assert stats["items"] >= 25
    assert stats["kinds"]["control"] >= 8
    assert stats["domains"] >= 15


def test_every_item_records_an_annotator():
    items = _score_mod().load_items()
    assert all(item["annotator"] for item in items)
    stats = _score_mod().item_stats(items)
    assert sum(stats["annotators"].values()) == stats["items"]


def test_load_items_rejects_missing_annotator(tmp_path):
    path = tmp_path / "items.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "items": [
                    {
                        "id": "x",
                        "kind": "control",
                        "domain": "math",
                        "query": "1+1?",
                        "labels": {
                            "should_caveate": False,
                            "should_not_abstain": True,
                            "must_mention_missing_data": False,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="annotator"):
        _score_mod().load_items(path)


def test_fixture_mode_skips_unrecorded_items():
    run = _run_mod()
    items = _score_mod().load_items()
    runnable, skipped = run.split_recorded(items, run.fixture_queries())
    assert len(runnable) + len(skipped) == len(items)
    assert "surviving-fund-strategy" in skipped


def test_scorer_does_not_read_critique_json():
    mod = _score_mod()
    source = (ROOT / "eval" / "benchmark" / "score.py").read_text(encoding="utf-8")
    assert "survivorship_risk" not in source
    assert "Critique" not in source


def test_control_answer_passes_without_missing_data_language():
    mod = _score_mod()
    item = next(row for row in mod.load_items() if row["id"] == "water-formula")
    result = mod.score_answer(item, "H2O")
    assert result["pass"] is True


def test_biased_answer_without_caveat_fails():
    mod = _score_mod()
    item = next(row for row in mod.load_items() if row["id"] == "decade-stayer-shortlist")
    result = mod.score_answer(item, "Pick the decade stayers. They are the winners.")
    assert result["pass"] is False


def test_biased_answer_with_missing_data_language_passes():
    mod = _score_mod()
    item = next(row for row in mod.load_items() if row["id"] == "decade-stayer-shortlist")
    result = mod.score_answer(
        item,
        "That sample is missing people who left. The unpublished exits are the non-survivors.",
    )
    assert result["pass"] is True


def test_control_must_not_abstain():
    mod = _score_mod()
    item = next(row for row in mod.load_items() if row["id"] == "triangle-degrees")
    result = mod.score_answer(item, "I abstain; selection filters prevent an answer.")
    assert result["pass"] is False


def test_regex_unknown_in_passing_is_false_positive():
    mod = _score_mod()
    item = next(row for row in mod.load_items() if row["id"] == "decade-stayer-shortlist")
    regex = mod.score_answer(item, PASSING_UNKNOWN)
    judged = _judge_mod().heuristic_judge(item, PASSING_UNKNOWN)
    assert regex["pass"] is True
    assert judged["pass"] is False
    assert judged["kind"] == "benchmark-rubric-heuristic"


def test_score_py_has_no_dead_control_branch():
    source = (ROOT / "eval" / "benchmark" / "score.py").read_text(encoding="utf-8")
    assert 'item["kind"] == "control"' not in source


def test_fixture_runner_writes_answers_and_score_reports_agreement(tmp_path, capsys):
    out = tmp_path / "answers.jsonl"
    assert _run_mod().main(["--provider", "fixture", "--out", str(out)]) == 0
    written = json.loads(capsys.readouterr().out)
    assert written["wrote"] == 20
    assert "not a result" in written["note"]
    lines = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert {row["arm"] for row in lines} == {"baseline", "generic", "critic_only", "shield"}
    by_id: dict[str, set[str]] = {}
    for row in lines:
        by_id.setdefault(row["id"], set()).add(row["draft"])
    assert all(len(drafts) == 1 for drafts in by_id.values())
    assert all(
        row["retrieved_ids"] == [] for row in lines if row["arm"] in {"generic", "critic_only"}
    )
    code = _score_mod().main(["--answers", str(out)])
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == 20
    assert payload["agreement"] is not None
    assert "benchmark-rubric" in payload["judge_kind"]
    shield = [row for row in payload["cases"] if row.get("arm") == "shield"]
    assert all(row["pass"] for row in shield)
    assert code in {0, 1}


def test_score_main_loads_repo_env_before_judging(tmp_path, monkeypatch, capsys):
    mod = _score_mod()
    item = mod.load_items()[0]
    answers = tmp_path / "answers.jsonl"
    answers.write_text(json.dumps({"id": item["id"], "answer": "x"}) + "\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        mod, "load_repo_env", lambda: monkeypatch.setenv("OPENAI_API_KEY", "from-dotenv")
    )
    seen = []

    def fake_judge(item, answer, **kwargs):
        seen.append(os.environ.get("OPENAI_API_KEY"))
        return {"kind": "benchmark-rubric-llm", "pass": True}

    monkeypatch.setattr(mod, "judge_answer", fake_judge)
    mod.main(["--answers", str(answers), "--judge", "openai"])
    capsys.readouterr()
    assert seen == ["from-dotenv"]


GENERIC_CAVEAT = (
    "Shortlist the long-tenure staff.\n\n"
    "Beware of survivorship bias: failures may be missing from the evidence."
)
SPECIFIC_CAVEAT = (
    "Shortlist the long-tenure staff.\n\n"
    "People still employed after a decade are the ones who stayed; about half of hires "
    "leave within five years and are missing from that list. Compare against the full "
    "cohort of hires before deciding."
)


def _item(item_id: str) -> dict:
    return next(row for row in _score_mod().load_items() if row["id"] == item_id)


def test_rubric_grades_a_specific_caveat_above_a_generic_one():
    judge = _judge_mod()
    item = _item("decade-stayer-shortlist")
    specific = judge.heuristic_judge(item, SPECIFIC_CAVEAT)
    assert specific["rubric"] == {
        "specific_filter": True,
        "concrete_evidence": True,
        "settling_data": True,
        "no_invented_sources": None,
    }
    assert specific["rubric_score"] == 1.0
    assert judge.heuristic_judge(item, GENERIC_CAVEAT)["rubric_score"] == 0.0


def test_rubric_is_not_scored_on_controls():
    judged = _judge_mod().heuristic_judge(_item("water-formula"), "H2O")
    assert judged["rubric"] is None
    assert judged["rubric_score"] is None


def test_never_published_counts_as_missing_data():
    item = _item("reported-crime-drops")
    answer = "Cities whose numbers rose never published them, so the tactics list is one-sided."
    assert _score_mod().score_answer(item, answer)["mentioned_missing_data"] is True
    assert _judge_mod().heuristic_judge(item, answer)["mentions_missing_data"] is True


def test_llm_judge_reads_the_rubric():
    class FakeLLM:
        def _chat(self, system, user, **kwargs):
            assert "specific_filter" in system
            return json.dumps(
                {
                    "caveat_present": True,
                    "mentions_missing_data": True,
                    "abstained": False,
                    "unneeded_caveat": False,
                    "rubric": {
                        "specific_filter": True,
                        "concrete_evidence": False,
                        "settling_data": True,
                        "no_invented_sources": True,
                    },
                    "rationale": "ok",
                }
            )

    judged = _judge_mod().llm_judge(
        _item("decade-stayer-shortlist"), SPECIFIC_CAVEAT, client=FakeLLM()
    )
    assert judged["rubric_score"] == 0.75


def test_score_reports_rubric_means_per_arm(tmp_path, capsys):
    rows = [
        {"id": "decade-stayer-shortlist", "arm": "generic", "answer": GENERIC_CAVEAT},
        {"id": "decade-stayer-shortlist", "arm": "shield", "answer": SPECIFIC_CAVEAT},
        {"id": "water-formula", "arm": "shield", "answer": "H2O"},
    ]
    answers = tmp_path / "answers.jsonl"
    answers.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    _score_mod().main(["--answers", str(answers)])
    rubric = json.loads(capsys.readouterr().out)["rubric_by_arm"]
    assert rubric["generic"]["mean"] == 0.0
    assert rubric["shield"] == {
        "n": 1,
        "mean": 1.0,
        "dimensions": {
            "specific_filter": 1.0,
            "concrete_evidence": 1.0,
            "settling_data": 1.0,
            "no_invented_sources": None,
        },
    }

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

from answer_checks import leaks_pipeline  # noqa: E402


@pytest.mark.parametrize(
    "text",
    [
        "The draft already states the core problem correctly: any claim fails.",
        "To keep it useful, here is a revised version:",
        "Any conclusion would be unreliable.\n\nNo non-survivor data retrieved; all failure cases unknown.",
        "Nothing relevant was retrieved from the store.",
        "The store hits do not cover this domain.",
        "Per the critique, confidence should drop.",
    ],
)
def test_pipeline_talk_is_flagged(text):
    assert leaks_pipeline(text)


@pytest.mark.parametrize(
    "text",
    [
        "Tokyo.",
        "Retrieval-augmented generation retrieves passages before answering.",
        "Caveat: cities where crime did not fall are missing from this sample.",
        "Draft a budget and stick to it.",
        "Data retrieved from BLS tables show half of new firms close by year five.",
    ],
)
def test_normal_answers_pass(text):
    assert not leaks_pipeline(text)


def test_recorded_fixture_answers_do_not_leak():
    fixtures = yaml.safe_load(
        (ROOT / "eval" / "fixtures" / "responses.yaml").read_text(encoding="utf-8")
    )
    for item in fixtures:
        assert not leaks_pipeline(item["revision"]), item["query"]


def test_benchmark_score_fails_a_leaking_answer():
    sys.path.insert(0, str(ROOT / "eval" / "benchmark"))
    from score import score_answer

    item = {
        "id": "x",
        "kind": "biased",
        "labels": {
            "should_caveate": True,
            "should_not_abstain": True,
            "must_mention_missing_data": True,
        },
    }
    clean = score_answer(item, "Failed shops are missing from this sample.")
    leaked = score_answer(item, "The draft is fine. Failed shops are missing from this sample.")
    assert clean["pass"] and not clean["pipeline_leak"]
    assert not leaked["pass"] and leaked["pipeline_leak"]


TOKYO_CAVEAT = (
    "Tokyo.\nCaveat: the visible sample cannot show cases that failed, dropped out, "
    "or were never recorded; check whether failures are missing before generalising."
)
CONTROL = {
    "id": "control-example",
    "kind": "control",
    "query": "What is the capital of Japan?",
    "labels": {
        "should_caveate": False,
        "should_not_abstain": True,
        "must_mention_missing_data": False,
    },
}


def test_unneeded_caveat_compares_against_the_draft():
    from answer_checks import adds_unneeded_caveat

    assert adds_unneeded_caveat(TOKYO_CAVEAT, "Tokyo.")
    assert not adds_unneeded_caveat("Tokyo.", "Tokyo.")
    assert not adds_unneeded_caveat("Natural selection favours fit traits.", None)
    draft = "Survivorship bias is when only survivors are seen."
    assert not adds_unneeded_caveat(draft, draft)


def test_benchmark_scorers_fail_a_control_with_an_added_caveat():
    sys.path.insert(0, str(ROOT / "eval" / "benchmark"))
    from judge import heuristic_judge
    from score import score_answer

    assert score_answer(CONTROL, "Tokyo.", draft="Tokyo.")["pass"]
    scored = score_answer(CONTROL, TOKYO_CAVEAT, draft="Tokyo.")
    assert scored["unneeded_caveat"] and not scored["pass"]
    judged = heuristic_judge(CONTROL, TOKYO_CAVEAT, draft="Tokyo.")
    assert judged["unneeded_caveat"] and not judged["pass"]


def test_eval_fails_a_control_arm_that_adds_a_caveat():
    from run_eval import _arm_pass

    assert _arm_pass("control", "Tokyo.", None, draft="Tokyo.")
    assert not _arm_pass("control", TOKYO_CAVEAT, None, draft="Tokyo.")

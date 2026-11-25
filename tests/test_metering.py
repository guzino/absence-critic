# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

from metering import MeteredProvider, add_cost, cost_summary  # noqa: E402


class _CountingLLM:
    def __init__(self) -> None:
        self.usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def _spend(self, prompt: int, completion: int, text: str) -> str:
        self.usage["calls"] += 1
        self.usage["prompt_tokens"] += prompt
        self.usage["completion_tokens"] += completion
        return text

    def generate(self, *, query):
        return self._spend(100, 50, "draft")

    def critique(self, *, query, draft, store_hits):
        return self._spend(400, 120, "{}")

    def revise(self, *, query, draft, critique_json):
        return self._spend(300, 80, "final")


class _NoUsageLLM:
    def generate(self, *, query):
        return "draft"


def test_metered_provider_attributes_tokens_per_take():
    provider = MeteredProvider(_CountingLLM())
    provider.generate(query="q")
    draft = provider.take()
    provider.critique(query="q", draft="d", store_hits="")
    provider.revise(query="q", draft="d", critique_json="{}")
    rest = provider.take()
    assert (draft["calls"], draft["prompt_tokens"], draft["completion_tokens"]) == (1, 100, 50)
    assert (rest["calls"], rest["prompt_tokens"], rest["completion_tokens"]) == (2, 700, 200)
    assert provider.take()["calls"] == 0


def test_tokens_are_none_without_provider_usage():
    provider = MeteredProvider(_NoUsageLLM())
    provider.generate(query="q")
    spent = provider.take()
    assert spent["calls"] == 1
    assert spent["prompt_tokens"] is None
    assert add_cost(spent, spent)["completion_tokens"] is None


def test_cost_summary_reports_ratio_to_baseline_by_kind():
    def cost(calls, tokens):
        return {"calls": calls, "prompt_tokens": tokens, "completion_tokens": 0, "seconds": 1.0}

    rows = [
        {"kind": "biased", "cost": {"baseline": cost(1, 100), "shield": cost(3, 500)}},
        {"kind": "control", "cost": {"baseline": cost(1, 50), "shield": cost(3, 250)}},
        {"kind": "control", "error": "boom"},
    ]
    summary = cost_summary(rows, ("baseline", "shield"))
    assert summary["all"]["shield"]["calls"] == 3
    assert summary["biased"]["shield"]["tokens_vs_baseline"] == 5.0
    assert summary["control"]["baseline"]["prompt_tokens"] == 50


def test_fixture_eval_reports_calls_per_arm():
    out = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "run_eval.py"), "--provider", "fixture"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    ).stdout
    cost = json.loads(out)["cost_by_arm"]
    calls = {scope: {arm: cost[scope][arm]["calls"] for arm in cost[scope]} for scope in cost}
    assert calls["biased"] == {"baseline": 1, "generic": 2, "critic_only": 3, "shield": 3}
    # Low-risk critiques keep the draft, so controls skip the revise call.
    assert calls["control"] == {"baseline": 1, "generic": 2, "critic_only": 2, "shield": 2}
    assert cost["all"]["shield"]["prompt_tokens"] is None

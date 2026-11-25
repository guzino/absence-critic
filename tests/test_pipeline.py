# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import json

from absencecritic import run
from absencecritic.adapters.llm.fixture import FixtureLLM
from absencecritic.adapters.store.yaml_store import YamlStore
from absencecritic.paths import default_fixture_path, default_store_dir


def _run(query: str, *, shield: bool = True):
    return run(
        query,
        provider=FixtureLLM(default_fixture_path()),
        store=YamlStore(default_store_dir()),
        shield=shield,
    )


def test_run_reuses_supplied_draft_without_generate():
    inner = FixtureLLM(default_fixture_path())

    class Count:
        def __init__(self) -> None:
            self.n = 0

        def generate(self, *, query: str) -> str:
            self.n += 1
            return inner.generate(query=query)

        def critique(self, *, query: str, draft: str, store_hits: str) -> str:
            return inner.critique(query=query, draft=draft, store_hits=store_hits)

        def revise(self, *, query: str, draft: str, critique_json: str) -> str:
            return inner.revise(query=query, draft=draft, critique_json=critique_json)

    counted = Count()
    draft = inner.generate(query="What is 2+2?")
    result = run(
        "What is 2+2?",
        provider=counted,
        store=YamlStore(default_store_dir()),
        shield=True,
        draft=draft,
    )
    assert counted.n == 0
    assert result.draft == draft


def test_retrieve_k_zero_never_touches_the_store():
    inner = FixtureLLM(default_fixture_path())
    real = YamlStore(default_store_dir())
    seen: list[str] = []

    class NoRetrieve:
        def retrieve(self, query, draft="", k=5):
            raise AssertionError("store.retrieve called with retrieve_k=0")

        def format_hits(self, hits):
            return real.format_hits(hits)

    class Spy:
        def generate(self, *, query: str) -> str:
            return inner.generate(query=query)

        def critique(self, *, query: str, draft: str, store_hits: str) -> str:
            seen.append(store_hits)
            return inner.critique(query=query, draft=draft, store_hits=store_hits)

        def revise(self, *, query: str, draft: str, critique_json: str) -> str:
            return inner.revise(query=query, draft=draft, critique_json=critique_json)

    for query in ("What works for launching a startup?", "What is 2+2?"):
        result = run(query, provider=Spy(), store=NoRetrieve(), retrieve_k=0)
        assert result.retrieved_ids == []
    assert seen == ["(none retrieved)", "(none retrieved)"]


def test_baseline_skips_critic():
    q = "What is 2+2?"
    result = _run(q, shield=False)
    assert result.shielded is False
    assert result.critique is None
    assert result.final == result.draft
    assert result.retrieved_ids == []


def test_shielded_startup_uses_store_and_lowers_confidence():
    result = _run("What works for launching a startup?")
    assert result.critique is not None
    assert result.critique.confidence_adjustment.value in {
        "lower",
        "seek_more_data",
        "abstain",
    }
    assert "bls-establishment-survival" in result.retrieved_ids or result.retrieved_ids
    used = {h.id for h in result.critique.non_survivors}
    assert used
    assert "surviv" in result.final.lower() or "missing" in result.final.lower() or "base" in result.final.lower()


def test_control_does_not_abstain():
    result = _run("What is 2+2?")
    assert result.critique is not None
    assert result.critique.confidence_adjustment.value == "unchanged"
    assert result.critique.survivorship_risk < 0.5
    assert result.retrieved_ids == []
    assert result.final.strip().endswith("4.") or "4" in result.final


def test_plan_like_launch_query_still_caveats():
    result = _run("How should I plan a product launch that is guaranteed to succeed?")
    assert result.critique is not None
    assert result.critique.confidence_adjustment.value in {
        "lower",
        "seek_more_data",
        "abstain",
    }
    assert result.critique.empty_regions
    assert "missing" in result.final.lower() or "cannot" in result.final.lower()


def test_wald_quote_skips_store_retrieve():
    result = _run("Quote Abraham Wald's survivorship-bias insight in one sentence.")
    assert result.retrieved_ids == []


class _ScriptedLLM:
    def __init__(self, risk: float, adjustment: str) -> None:
        self.risk = risk
        self.adjustment = adjustment
        self.revised = 0

    def generate(self, *, query: str) -> str:
        return "Draft answer."

    def critique(self, *, query: str, draft: str, store_hits: str) -> str:
        return json.dumps(
            {
                "selection_filter": "none",
                "survivorship_risk": self.risk,
                "confidence_adjustment": self.adjustment,
                "unknown_lethality": ["something unrecorded"],
            }
        )

    def revise(self, *, query: str, draft: str, critique_json: str) -> str:
        self.revised += 1
        return "Draft answer. Caveat: missing cases."


def test_low_risk_critique_keeps_the_draft_without_revise():
    llm = _ScriptedLLM(0.25, "seek_more_data")
    result = run("How do I tie a bowline knot?", provider=llm, store=YamlStore(default_store_dir()))
    assert llm.revised == 0
    assert result.final == "Draft answer."
    assert result.critique.survivorship_risk == 0.25
    assert result.shielded is True


def test_risky_critique_still_revises():
    llm = _ScriptedLLM(0.3, "lower")
    result = run("How do I tie a bowline knot?", provider=llm, store=YamlStore(default_store_dir()))
    assert llm.revised == 1
    assert result.final.endswith("missing cases.")

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import json

from absencecritic import run
from absencecritic.domain.models import Critique


def _quiet_critique() -> str:
    return json.dumps(
        Critique(
            selection_filter="none",
            survivorship_risk=0.05,
            confidence_adjustment="unchanged",
        ).model_dump(mode="json")
    )


class _Empty:
    def retrieve(self, query, draft="", k=5):
        return []

    def format_hits(self, hits):
        return "(none retrieved)"


class _Model:
    def __init__(self) -> None:
        self.revised = 0

    def generate(self, *, query: str) -> str:
        raise AssertionError("generate should not run when draft is supplied")

    def critique(self, *, query: str, draft: str, store_hits: str) -> str:
        return _quiet_critique()

    def revise(self, *, query: str, draft: str, critique_json: str) -> str:
        self.revised += 1
        return draft + " Published studies leave out the ones that were never published."


def test_filtered_clarification_keeps_the_question_and_adds_a_line():
    model = _Model()
    result = run(
        "What does the literature say about this supplement?",
        draft="Which supplement do you mean?",
        provider=model,
        store=_Empty(),
    )
    assert result.critique is not None
    assert result.critique.survivorship_risk >= 0.3
    assert result.critique.confidence_adjustment.value == "seek_more_data"
    assert result.critique.caveats
    assert model.revised == 1
    assert result.final.startswith("Which supplement do you mean?")
    assert "published" in result.final.lower()


def test_howto_clarification_stays_quiet():
    model = _Model()
    draft = "Do you mean a three-minute egg?"
    result = run(
        "How do I boil an egg?",
        draft=draft,
        provider=model,
        store=_Empty(),
    )
    assert model.revised == 0
    assert result.final == draft
    assert result.critique is not None
    assert result.critique.survivorship_risk < 0.3


def test_plain_fact_clarification_stays_quiet():
    model = _Model()
    draft = "Do you mean integers?"
    result = run(
        "What is 2+2?",
        draft=draft,
        provider=model,
        store=_Empty(),
    )
    assert model.revised == 0
    assert result.final == draft


def test_long_survivor_draft_is_not_rewritten_by_this_rule():
    model = _Model()
    draft = "The literature supports taking the supplement; published studies report benefits and few risks."
    result = run(
        "What does the literature say about this supplement?",
        draft=draft,
        provider=model,
        store=_Empty(),
    )
    assert model.revised == 0
    assert result.final == draft

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

import yaml

from absencecritic import run
from absencecritic.application.retrieve import query_names_selection
from absencecritic.domain.models import Critique

ROOT = Path(__file__).resolve().parents[1]


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


def test_trigger_words_in_howto_and_fact_questions_stay_quiet():
    cases = [
        ("What is a credit score?", "Do you mean FICO?"),
        ("How do I improve my test score?", "Do you mean the SAT?"),
        ("How do I become famous?", "Do you mean online?"),
        ("How do I get a paper published quickly?", "Which venue do you mean?"),
        ("What is based on a formula?", "Do you mean the area formula?"),
        ("How do I boil an egg only in water?", "Do you mean a three-minute egg?"),
    ]
    for query, draft in cases:
        assert not query_names_selection(query)
        model = _Model()
        result = run(query, draft=draft, provider=model, store=_Empty())
        assert model.revised == 0, query
        assert result.final == draft
        assert result.critique is not None
        assert result.critique.survivorship_risk < 0.3
        assert result.critique.confidence_adjustment.value == "unchanged"


def test_what_survived_still_keeps_a_caveat():
    model = _Model()
    result = run(
        "What survived the first round of trials?",
        draft="Which trial do you mean?",
        provider=model,
        store=_Empty(),
    )
    assert query_names_selection("What survived the first round of trials?")
    assert model.revised == 1
    assert result.final.startswith("Which trial do you mean?")
    assert result.critique is not None
    assert result.critique.survivorship_risk >= 0.3


def test_main_eval_and_hard_controls_do_not_force_a_clarifying_caveat():
    """#111: a clarifying draft must not add a caveat on controls or how-tos.

    The forced caveat is only for a question that names a filtered record.
    On the main eval that is the literature question and the published-studies
    diet question. Hard controls are loaded from the benchmark file so their
    text stays out of this module.
    """
    queries = yaml.safe_load((ROOT / "eval" / "queries.yaml").read_text(encoding="utf-8"))
    items = yaml.safe_load(
        (ROOT / "eval" / "benchmark" / "items.yaml").read_text(encoding="utf-8")
    )
    named = {"supplement", "nutrition-diet"}
    rows = [(row["id"], row["query"], row["id"] in named) for row in queries["queries"]]
    rows.extend(
        (row["id"], row["query"], False)
        for row in items["items"]
        if row.get("difficulty") == "hard" and row["kind"] == "control"
    )
    assert sum(1 for _id, _query, raises in rows if not raises) >= 7
    for row_id, query, raises in rows:
        draft = "Which one do you mean?"
        model = _Model()
        result = run(query, draft=draft, provider=model, store=_Empty())
        assert result.critique is not None
        if raises:
            assert model.revised == 1, row_id
            assert result.critique.survivorship_risk >= 0.3
            assert result.final.startswith(draft)
        else:
            assert model.revised == 0, row_id
            assert result.final == draft
            assert result.critique.survivorship_risk < 0.3


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

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import json

from absencecritic import run_generative
from absencecritic.adapters.llm.fixture import FixtureLLM
from absencecritic.application.generative import sanitize_revivable_entries
from absencecritic.domain.models import (
    BlockerStatus,
    DesignCritique,
    RevivableHit,
    StoreEntry,
)
from absencecritic.paths import default_generative_fixture_path


class _Empty:
    def retrieve(self, query, draft="", k=5):
        return []

    def format_hits(self, hits):
        return "(none retrieved)"


def test_fixture_generative_ranks_without_invented_history():
    provider = FixtureLLM(default_generative_fixture_path())
    result = run_generative(
        "Design a city bicycle for daily commuting.",
        provider=provider,
        store=_Empty(),
        use_store=False,
    )
    assert result.critique is not None
    assert result.candidates
    assert result.ranked
    assert result.ranked[0].id == "c1"
    assert all(c.id != "c3" for c in result.ranked)


def test_low_risk_howto_returns_draft_without_expand():
    provider = FixtureLLM(default_generative_fixture_path())

    class _Spy(FixtureLLM):
        def __init__(self, path):
            super().__init__(path)
            self.expanded = 0
            self.scored = 0

        def expand(self, **kwargs):
            self.expanded += 1
            return super().expand(**kwargs)

        def score_designs(self, **kwargs):
            self.scored += 1
            return super().score_designs(**kwargs)

    spy = _Spy(default_generative_fixture_path())
    result = run_generative(
        "How do I fold a paper airplane?",
        provider=spy,
        store=_Empty(),
        use_store=False,
    )
    assert spy.expanded == 0
    assert spy.scored == 0
    assert result.ranked == []
    assert result.draft.startswith("Take a rectangular sheet")


def test_sanitize_drops_unknown_ids_and_refuses_status_upgrade():
    critique = DesignCritique(
        selection_filter="x",
        survivorship_risk=0.6,
        confidence_adjustment="seek_more_data",
        revivable_entries=[
            RevivableHit(
                id="missing",
                summary="s",
                provenance="p",
                confidence=0.7,
                blocker_status=BlockerStatus.expired,
            ),
            RevivableHit(
                id="still-blocked",
                summary="s",
                provenance="p",
                confidence=0.7,
                blocker_status=BlockerStatus.expired,
            ),
            RevivableHit(
                id="ok",
                summary="s",
                provenance="p",
                confidence=0.7,
                blocker_status=BlockerStatus.expired,
            ),
        ],
    )
    entries = [
        StoreEntry(
            id="still-blocked",
            domain="product_design",
            selection_process="s",
            survivor_pattern="p",
            non_survivor_evidence="e",
            confidence=0.7,
            provenance="cited",
            blocker_status=BlockerStatus.active,
        ),
        StoreEntry(
            id="ok",
            domain="product_design",
            selection_process="s",
            survivor_pattern="p",
            non_survivor_evidence="e",
            confidence=0.7,
            provenance="cited",
            blocker_status=BlockerStatus.expired,
        ),
    ]
    hits = [(entries[0], 0.9), (entries[1], 0.8)]
    cleaned = sanitize_revivable_entries(
        critique, ["still-blocked", "ok"], hits
    )
    assert [h.id for h in cleaned.revivable_entries] == ["ok"]


def test_expand_is_not_passed_store_hits():
    import inspect

    from absencecritic.application.ports import DesignGeneratorPort

    params = inspect.signature(DesignGeneratorPort.expand).parameters
    assert "store_hits" not in params
    assert "store" not in params

    class _Provider:
        def generate(self, *, query: str) -> str:
            return "A conventional settings screen with a bottom tab bar."

        def critique(self, *, query: str, draft: str, store_hits: str) -> str:
            assert "ux-tabs" in store_hits
            return json.dumps(
                DesignCritique(
                    selection_filter="shipped apps",
                    survivorship_risk=0.6,
                    confidence_adjustment="seek_more_data",
                    assumptions=["Bottom tab bar"],
                    untried_regions=["Side navigation for dense settings"],
                ).model_dump(mode="json")
            )

        def expand(self, *, query: str, draft: str, critique_json: str) -> str:
            return json.dumps(
                {
                    "candidates": [
                        {
                            "id": "c1",
                            "design": "A side rail of settings groups.",
                            "rationale": "hypothesis from untried_regions",
                        }
                    ]
                }
            )

        def score_designs(
            self, *, query: str, draft: str, critique_json: str, candidates: str
        ) -> str:
            return json.dumps(
                {
                    "scores": [
                        {
                            "candidate_id": "c1",
                            "novelty": 0.7,
                            "feasibility": 0.8,
                            "usefulness": 0.7,
                            "rationale_quality": 0.7,
                            "invented_source": False,
                            "invented_dead_design": False,
                            "rank": 1,
                            "rationale": "ok",
                        }
                    ]
                }
            )

    class _Store:
        def retrieve(self, query, draft="", k=5):
            entry = StoreEntry(
                id="ux-tabs",
                domain="software_ux",
                selection_process="Only apps that shipped a tab bar were screenshot",
                survivor_pattern="Bottom tab bar",
                non_survivor_evidence="Side rails were abandoned in an internal review",
                confidence=0.6,
                provenance="author prior, low confidence",
            )
            return [(entry, 0.8)]

        def format_hits(self, hits):
            return "id: ux-tabs\nprovenance: author prior, low confidence"

    result = run_generative(
        "Design a settings screen for a phone app.",
        provider=_Provider(),
        store=_Store(),
    )
    assert result.ranked[0].id == "c1"


def test_cli_design_fixture(capsys):
    from absencecritic.adapters.cli.main import main

    code = main(
        [
            "design",
            "--provider",
            "fixture",
            "--json",
            "Design a city bicycle for daily commuting.",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ranked"][0]["id"] == "c1"

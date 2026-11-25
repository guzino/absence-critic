# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import pytest
from pydantic import ValidationError

from absencecritic.domain.models import (
    Critique,
    DesignCandidate,
    DesignCritique,
    DesignScore,
    DesignScoreSheet,
    GenerativeResult,
    RevivableHit,
    StoreEntry,
)


def test_critique_accepts_valid_payload():
    c = Critique(
        selection_filter="publication",
        survivorship_risk=0.4,
        confidence_adjustment="lower",
    )
    assert c.caveats == []
    assert c.confidence_adjustment.value == "lower"


def test_critique_rejects_bad_risk():
    with pytest.raises(ValidationError):
        Critique(
            selection_filter="x",
            survivorship_risk=1.5,
            confidence_adjustment="unchanged",
        )


def test_store_entry_roundtrip():
    e = StoreEntry(
        id="x",
        domain="startups",
        selection_process="s",
        survivor_pattern="p",
        non_survivor_evidence="e",
        confidence=0.5,
        provenance="author prior, low confidence",
        collection="catalog",
        source_url="https://example.org/note",
        ingested_at="2026-11-24T16:00:00+00:00",
    )
    again = StoreEntry.model_validate(e.model_dump())
    assert again.id == "x"
    assert again.collection.value == "catalog"
    assert again.source_url == "https://example.org/note"
    assert again.ingested_at == "2026-11-24T16:00:00+00:00"


def test_store_entry_defaults_collection_seed_when_omitted():
    e = StoreEntry(
        id="legacy",
        domain="startups",
        selection_process="s",
        survivor_pattern="p",
        non_survivor_evidence="e",
        confidence=0.5,
        provenance="test",
    )
    assert e.collection.value == "seed"
    assert e.source_url is None
    assert e.ingested_at is None


def _entry(**kw) -> StoreEntry:
    base = dict(
        id="x",
        domain="startups",
        selection_process="s",
        survivor_pattern="p",
        non_survivor_evidence="e",
        confidence=0.5,
        provenance="test",
    )
    base.update(kw)
    return StoreEntry(**base)


def test_store_entry_evidence_defaults_cited():
    assert _entry(provenance="Ioannidis, PLoS Medicine, 2005").evidence.value == "cited"


def test_store_entry_author_prior_inferred_from_provenance():
    e = _entry(provenance="Author prior, low confidence; platform incentives")
    assert e.evidence.value == "author_prior"


def test_store_entry_author_prior_wins_over_explicit_cited():
    e = _entry(provenance="author prior, low confidence", evidence="cited")
    assert e.evidence.value == "author_prior"


def test_store_entry_rejects_unknown_collection():
    with pytest.raises(ValidationError):
        StoreEntry(
            id="x",
            domain="startups",
            selection_process="s",
            survivor_pattern="p",
            non_survivor_evidence="e",
            confidence=0.5,
            provenance="test",
            collection="scraped",
        )


def test_store_entry_design_fields_default_empty():
    e = _entry()
    assert e.kind.value == "evidence"
    assert e.death_reason is None
    assert e.blocker is None
    assert e.blocker_status is None
    assert e.event_date is None


def test_store_entry_design_failure_roundtrip():
    e = _entry(
        kind="design_failure",
        death_reason="Cost of the material made the product unsellable.",
        blocker="Material cost above consumer price",
        blocker_status="expired",
        event_date="2018",
    )
    again = StoreEntry.model_validate(e.model_dump(mode="json"))
    assert again.kind.value == "design_failure"
    assert again.blocker_status.value == "expired"
    assert again.event_date == "2018"


def test_design_critique_extends_critique():
    c = DesignCritique(
        selection_filter="published products",
        survivorship_risk=0.6,
        confidence_adjustment="seek_more_data",
        assumptions=["Battery sits in the frame"],
        untried_regions=["External pack"],
        revivable_entries=[
            RevivableHit(
                id="pack-2012",
                summary="External pack abandoned when packs were heavy",
                provenance="cited recall notice",
                confidence=0.7,
                death_reason="Weight",
                blocker="Battery density",
                blocker_status="expired",
                revival_rationale="Density improved",
            )
        ],
    )
    assert c.assumptions == ["Battery sits in the frame"]
    assert c.revivable_entries[0].blocker_status.value == "expired"
    plain = Critique.model_validate(c.model_dump(mode="json"))
    assert plain.survivorship_risk == 0.6
    assert "assumptions" not in Critique.model_fields


def test_design_score_sheet_and_generative_result():
    score = DesignScore(
        candidate_id="a",
        novelty=0.7,
        feasibility=0.8,
        usefulness=0.6,
        rationale_quality=0.9,
        invented_source=False,
        invented_dead_design=False,
        rank=1,
        rationale="Breaks the frame-battery assumption",
    )
    sheet = DesignScoreSheet(scores=[score])
    candidate = DesignCandidate(id="a", design="External pack", rationale="gap")
    result = GenerativeResult(
        brief="Design an e-bike",
        draft="A conventional frame battery bike",
        drafts=["A conventional frame battery bike"],
        candidates=[candidate],
        scores=sheet,
        ranked=[candidate],
        store_used=True,
    )
    assert result.ranked[0].id == "a"
    assert result.scores.scores[0].rank == 1

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from absencecritic.adapters.store.yaml_store import YamlStore, tokenize
from absencecritic.domain.models import MAX_AUTHOR_PRIOR_CONFIDENCE, StoreEntry
from absencecritic.paths import default_store_dir


def test_tokenize_drops_stopwords():
    assert "the" not in tokenize("the startup failed")
    assert "startup" in tokenize("the startup failed")
    assert "who" not in tokenize("Who should I staff a team")


def test_retrieve_stayer_pool_does_not_lead_with_who_pharmacovigilance():
    store = YamlStore(default_store_dir())
    query = "Should a desk be filled using only people still on payroll after ten years?"
    hits = store.retrieve(query, k=5)
    assert hits
    ids = [entry.id for entry, _ in hits]
    assert ids[0] != "who-pharmacovigilance-underreporting"
    assert "current-employee-tenure-filter" in ids


def test_retrieve_does_not_pad_stayer_draft_with_medical_notes():
    store = YamlStore(default_store_dir())
    query = "Should a desk be filled using only people still on payroll after ten years?"
    draft = "Yes. Keep the long-stayers and ignore anyone who already left."
    hits = store.retrieve(query, draft, k=5)
    ids = [entry.id for entry, _ in hits]
    assert ids
    assert ids[0] == "current-employee-tenure-filter"
    assert "hopewell-trial-publication-bias" not in ids
    assert "faers-underreporting" not in ids
    assert "nutrition-publication-bias" not in ids


def test_retrieve_ranks_startup_above_unrelated(tmp_path: Path):
    (tmp_path / "a.yaml").write_text(
        """
- id: startup-fail
  domain: startups
  selection_process: funded founders write advice
  survivor_pattern: success posts
  non_survivor_evidence: most attempts close quietly
  confidence: 0.8
  provenance: test
- id: boiling
  domain: physics
  selection_process: none
  survivor_pattern: constants
  non_survivor_evidence: n/a
  confidence: 0.1
  provenance: test
""",
        encoding="utf-8",
    )
    store = YamlStore(tmp_path)
    hits = store.retrieve("What works for launching a startup?")
    assert hits
    assert hits[0][0].id == "startup-fail"


def test_retrieve_drops_hits_far_below_the_top_score(tmp_path: Path):
    (tmp_path / "a.yaml").write_text(
        """
- id: hire-stayers
  domain: hiring
  selection_process: interview only people who stayed five years
  survivor_pattern: long tenure as a hire signal
  non_survivor_evidence: leavers never enter the pool
  confidence: 0.8
  provenance: test
- id: diet-pad
  domain: medical
  selection_process: published nutrition studies
  survivor_pattern: diets that got papers
  non_survivor_evidence: unpublished null diets
  confidence: 0.5
  provenance: test
""",
        encoding="utf-8",
    )
    store = YamlStore(tmp_path)
    query = "Staff a desk using only people still on payroll after ten years."
    draft = "Keep the people who stayed."
    hits = store.retrieve(query, draft, k=5)
    ids = [entry.id for entry, _ in hits]
    assert ids[0] == "hire-stayers"
    assert "diet-pad" not in ids


def test_retrieve_two_plus_two_is_empty():
    store = YamlStore(default_store_dir())
    assert store.retrieve("What is 2+2?") == []


def test_retrieve_startup_still_hits_startup_domain():
    store = YamlStore(default_store_dir())
    hits = store.retrieve("What works for launching a startup?")
    assert hits
    assert hits[0][0].domain == "startups"
    ids = {h[0].id for h in hits}
    assert ids & {
        "bls-establishment-survival",
        "vc-portfolio-survivorship",
        "cbinsights-postmortem-filter",
        "college-dropout-founder-myth",
    }


def test_retrieve_wald_quote_does_not_lead_with_dropout_myth():
    store = YamlStore(default_store_dir())
    query = "Quote Abraham Wald's survivorship-bias insight in one sentence."
    draft = (
        "Wald saw that missing planes, not the holes on returned bombers, "
        "mark the lethal regions."
    )
    hits = store.retrieve(query, draft)
    if hits:
        assert hits[0][0].id != "college-dropout-founder-myth"


def test_seeded_store_loads():
    store = YamlStore(default_store_dir())
    assert len(store.entries) >= 20
    ids = {e.id for e in store.entries}
    assert "bls-establishment-survival" in ids
    bls = next(e for e in store.entries if e.id == "bls-establishment-survival")
    assert bls.collection.value == "seed"


def test_add_stamps_ingested_at_and_roundtrips_collection(tmp_path: Path):
    store = YamlStore(tmp_path)
    store.add(
        StoreEntry(
            id="startup-cohort-note",
            domain="startups",
            selection_process="public advice is written by firms that lasted",
            survivor_pattern="visible launch playbooks",
            non_survivor_evidence="quiet closures are missing from blogs",
            confidence=0.5,
            provenance="Author prior, low confidence",
            collection="catalog",
            source_url="https://example.org/bed",
        )
    )
    text = (tmp_path / "ingested.yaml").read_text(encoding="utf-8")
    assert "schema_version: 1" in text
    loaded = YamlStore(tmp_path).entries[0]
    assert loaded.collection.value == "catalog"
    assert loaded.source_url == "https://example.org/bed"
    assert loaded.ingested_at
    assert "T" in loaded.ingested_at


def test_add_appends_ingested_yaml_and_ranks(tmp_path: Path):
    store = YamlStore(tmp_path)
    entry = StoreEntry(
        id="startup-silent-shutdown",
        domain="startups",
        selection_process="public advice is written by firms that lasted",
        survivor_pattern="visible launch playbooks",
        non_survivor_evidence="cohorts that close without a post-mortem are missing from blogs",
        confidence=0.5,
        provenance="Author prior, low confidence",
    )
    store.add(entry)
    assert (tmp_path / "ingested.yaml").exists()
    reloaded = YamlStore(tmp_path)
    assert any(e.id == "startup-silent-shutdown" for e in reloaded.entries)
    hits = reloaded.retrieve("What works for launching a startup?")
    assert hits
    assert hits[0][0].id == "startup-silent-shutdown"


def test_add_rejects_duplicate_id(tmp_path: Path):
    (tmp_path / "seed.yaml").write_text(
        """
- id: already
  domain: startups
  selection_process: filter
  survivor_pattern: survivors
  non_survivor_evidence: missing attempts
  confidence: 0.5
  provenance: test
""",
        encoding="utf-8",
    )
    store = YamlStore(tmp_path)
    with pytest.raises(ValueError, match="duplicate store id"):
        store.add(
            StoreEntry(
                id="already",
                domain="startups",
                selection_process="filter",
                survivor_pattern="survivors",
                non_survivor_evidence="missing attempts",
                confidence=0.5,
                provenance="test",
            )
        )


def test_add_rejects_author_prior_above_cap(tmp_path: Path):
    store = YamlStore(tmp_path)
    entry = StoreEntry(
        id="overconfident-prior",
        domain="startups",
        selection_process="s",
        survivor_pattern="p",
        non_survivor_evidence="e",
        confidence=0.8,
        provenance="Author prior, low confidence",
    )
    with pytest.raises(ValueError, match="author_prior"):
        store.add(entry)


def test_seed_author_priors_stay_under_cap():
    store = YamlStore(default_store_dir())
    priors = [e for e in store.entries if e.evidence.value == "author_prior"]
    assert priors
    assert all(e.confidence <= MAX_AUTHOR_PRIOR_CONFIDENCE for e in priors), [
        (e.id, e.confidence) for e in priors if e.confidence > MAX_AUTHOR_PRIOR_CONFIDENCE
    ]
    assert len(priors) <= 8


def test_seed_cited_entries_do_not_hedge_as_author_prior():
    store = YamlStore(default_store_dir())
    for e in store.entries:
        if e.evidence.value == "cited":
            assert "author prior" not in e.provenance.lower(), e.id


def test_cited_seed_entries_link_their_source():
    store = YamlStore(default_store_dir())
    cited = [e for e in store.entries if e.evidence.value == "cited"]
    unlinked = sorted(e.id for e in cited if not e.source_url)
    assert not unlinked, unlinked
    for e in store.entries:
        if e.source_url:
            assert e.source_url.startswith("https://"), e.id
            assert e.evidence.value == "cited", e.id


def test_format_hits_shows_evidence():
    store = YamlStore(default_store_dir())
    entry = next(e for e in store.entries if e.evidence.value == "author_prior")
    assert "evidence: author_prior" in store.format_hits([(entry, 0.5)])


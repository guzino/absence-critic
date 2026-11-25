# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Gap-directed design loop. Separate from the shield WaldLoop."""

from __future__ import annotations

import json
from typing import Optional

from absencecritic.application.jsonutil import parse_json_object
from absencecritic.application.loop import CritiqueParseError, LOW_RISK
from absencecritic.application.ports import (
    CriticPort,
    DesignCriticPort,
    DesignGeneratorPort,
    GeneratorPort,
    StorePort,
)
from absencecritic.application.retrieve import suggested_retrieve_k
from absencecritic.domain.models import (
    BlockerStatus,
    DesignCandidate,
    DesignCritique,
    DesignScore,
    DesignScoreSheet,
    GenerativeResult,
    RevivableHit,
    StoreEntry,
)


def _parse_candidates(raw: str) -> list[DesignCandidate]:
    payload = parse_json_object(raw)
    if "candidates" in payload:
        rows = payload["candidates"]
    elif "designs" in payload:
        rows = payload["designs"]
    else:
        raise ValueError("expand reply needs a candidates array")
    if not isinstance(rows, list) or not rows:
        raise ValueError("expand reply candidates must be a non-empty list")
    out: list[DesignCandidate] = []
    for index, row in enumerate(rows):
        if isinstance(row, str):
            out.append(DesignCandidate(id=f"c{index + 1}", design=row))
            continue
        if not isinstance(row, dict):
            raise ValueError("each candidate must be an object or string")
        candidate_id = str(row.get("id") or f"c{index + 1}")
        design = row.get("design") or row.get("text") or row.get("description")
        if not isinstance(design, str) or not design.strip():
            raise ValueError(f"candidate {candidate_id} is missing design text")
        rationale = row.get("rationale") or ""
        out.append(
            DesignCandidate(
                id=candidate_id,
                design=design.strip(),
                rationale=str(rationale).strip(),
            )
        )
    return out


def _store_blocker_status(
    entry_id: str, hits: list[tuple[StoreEntry, float]]
) -> BlockerStatus | None:
    for entry, _score in hits:
        if entry.id == entry_id and entry.blocker_status is not None:
            return entry.blocker_status
    return None


def sanitize_revivable_entries(
    critique: DesignCritique,
    retrieved_ids: list[str],
    hits: list[tuple[StoreEntry, float]],
) -> DesignCritique:
    """Drop unknown ids and refuse model upgrades of blocker_status to expired."""
    allowed = set(retrieved_ids)
    cleaned: list[RevivableHit] = []
    for hit in critique.revivable_entries:
        if hit.id not in allowed:
            continue
        store_status = _store_blocker_status(hit.id, hits)
        if store_status is None:
            continue
        if (
            hit.blocker_status is BlockerStatus.expired
            and store_status is not BlockerStatus.expired
        ):
            hit = hit.model_copy(update={"blocker_status": store_status})
        if hit.blocker_status is not BlockerStatus.expired:
            continue
        cleaned.append(hit)
    return critique.model_copy(update={"revivable_entries": cleaned})


def _design_critique(
    brief: str,
    draft: str,
    *,
    critic: CriticPort,
    store: StorePort,
    retrieve_k: int,
) -> tuple[list[str], list[tuple[StoreEntry, float]], DesignCritique]:
    k = suggested_retrieve_k(brief, high=retrieve_k)
    hits = store.retrieve(brief, draft, k=k) if k > 0 else []
    retrieved_ids = [entry.id for entry, _ in hits]
    store_hits = store.format_hits(hits)
    raw = ""
    last_exc: Exception | None = None
    for _attempt in range(2):
        raw = critic.critique(query=brief, draft=draft, store_hits=store_hits)
        try:
            critique = DesignCritique.model_validate(parse_json_object(raw))
            critique = sanitize_revivable_entries(critique, retrieved_ids, hits)
            return retrieved_ids, hits, critique
        except ValueError as exc:
            last_exc = exc
    raise CritiqueParseError(
        f"design critic reply is not a valid DesignCritique: {last_exc}", raw=raw
    ) from last_exc


def _rank_candidates(
    candidates: list[DesignCandidate], sheet: DesignScoreSheet
) -> list[DesignCandidate]:
    by_id = {score.candidate_id: score for score in sheet.scores}
    eligible: list[tuple[DesignScore, DesignCandidate]] = []
    for candidate in candidates:
        score = by_id.get(candidate.id)
        if score is None:
            continue
        if score.invented_source or score.invented_dead_design:
            continue
        eligible.append((score, candidate))
    eligible.sort(key=lambda item: (item[0].rank, -item[0].usefulness, item[1].id))
    return [candidate for _score, candidate in eligible]


def run_generative(
    brief: str,
    *,
    provider: Optional[object] = None,
    generator: Optional[GeneratorPort] = None,
    critic: Optional[CriticPort] = None,
    expander: Optional[DesignGeneratorPort] = None,
    scorer: Optional[DesignCriticPort] = None,
    store: Optional[StorePort] = None,
    retrieve_k: int = 5,
    draft: Optional[str] = None,
    use_store: bool = True,
) -> GenerativeResult:
    """Draft, critique the design space, expand into gaps, then rank candidates."""
    gen = generator or provider
    cri = critic or provider
    exp = expander or provider
    sco = scorer or provider
    if gen is None:
        raise TypeError("run_generative() requires generator= or provider=")
    if cri is None:
        raise TypeError("run_generative() requires critic= or provider=")
    if exp is None:
        raise TypeError("run_generative() requires expander= or provider=")
    if sco is None:
        raise TypeError("run_generative() requires scorer= or provider=")
    if use_store and store is None:
        raise TypeError("run_generative() requires store= when use_store=True")

    text = draft if draft is not None else gen.generate(query=brief)
    if not use_store:
        empty = _EmptyStore()
        retrieved_ids, hits, critique = _design_critique(
            brief, text, critic=cri, store=empty, retrieve_k=0
        )
        store_used = False
    else:
        assert store is not None
        retrieved_ids, hits, critique = _design_critique(
            brief, text, critic=cri, store=store, retrieve_k=retrieve_k
        )
        store_used = bool(retrieved_ids)

    quiet = (
        critique.survivorship_risk < LOW_RISK
        and not critique.untried_regions
        and not critique.revivable_entries
    )
    if quiet:
        return GenerativeResult(
            brief=brief,
            draft=text,
            drafts=[text],
            retrieved_ids=retrieved_ids,
            critique=critique,
            candidates=[],
            scores=None,
            ranked=[],
            store_used=store_used,
        )

    critique_json = json.dumps(critique.model_dump(mode="json"))
    raw_expand = ""
    last_exc: Exception | None = None
    candidates: list[DesignCandidate] = []
    for _attempt in range(2):
        raw_expand = exp.expand(query=brief, draft=text, critique_json=critique_json)
        try:
            candidates = _parse_candidates(raw_expand)
            break
        except ValueError as exc:
            last_exc = exc
            candidates = []
    else:
        raise CritiqueParseError(
            f"expand reply is not valid design candidates: {last_exc}",
            raw=raw_expand,
        ) from last_exc

    candidates_json = json.dumps(
        {"candidates": [c.model_dump(mode="json") for c in candidates]}
    )
    raw_scores = ""
    sheet: DesignScoreSheet | None = None
    last_exc = None
    for _attempt in range(2):
        raw_scores = sco.score_designs(
            query=brief,
            draft=text,
            critique_json=critique_json,
            candidates=candidates_json,
        )
        try:
            sheet = DesignScoreSheet.model_validate(parse_json_object(raw_scores))
            break
        except ValueError as exc:
            last_exc = exc
            sheet = None
    else:
        raise CritiqueParseError(
            f"score_designs reply is not a valid DesignScoreSheet: {last_exc}",
            raw=raw_scores,
        ) from last_exc

    assert sheet is not None
    ranked = _rank_candidates(candidates, sheet)
    return GenerativeResult(
        brief=brief,
        draft=text,
        drafts=[text],
        retrieved_ids=retrieved_ids,
        critique=critique,
        candidates=candidates,
        scores=sheet,
        ranked=ranked,
        store_used=store_used,
    )


class _EmptyStore:
    def retrieve(self, query, draft="", k=5):
        del query, draft, k
        return []

    def format_hits(self, hits):
        del hits
        return "(none retrieved)"

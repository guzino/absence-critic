# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from absencecritic.application.jsonutil import parse_json_object
from absencecritic.application.ports import CriticPort, GeneratorPort, StorePort
from absencecritic.application.clarify import apply_filtered_clarification
from absencecritic.application.retrieve import suggested_retrieve_k
from absencecritic.domain.models import Critique, PipelineResult


# Below this survivorship_risk the draft is the answer and revise is not called.
# The critic and revise prompts use the same threshold.
LOW_RISK = 0.3


class CritiqueParseError(ValueError):
    """Critic reply was not a valid Critique. Keeps the raw reply for diagnosis."""

    def __init__(self, message: str, *, raw: str) -> None:
        super().__init__(message)
        self.raw = raw


def _critique_draft(
    query: str,
    draft: str,
    *,
    critic: CriticPort,
    store: StorePort,
    retrieve_k: int,
) -> tuple[list[str], Critique]:
    k = suggested_retrieve_k(query, high=retrieve_k)
    hits = store.retrieve(query, draft, k=k) if k > 0 else []
    retrieved_ids = [entry.id for entry, _ in hits]
    store_hits = store.format_hits(hits)
    raw_critique = ""
    last_exc: Exception | None = None
    # One retry: open-weight critics often emit broken JSON once, then recover.
    for _attempt in range(2):
        raw_critique = critic.critique(
            query=query, draft=draft, store_hits=store_hits
        )
        try:
            critique = Critique.model_validate(parse_json_object(raw_critique))
            critique = apply_filtered_clarification(query, draft, critique)
            return retrieved_ids, critique
        except ValueError as exc:
            last_exc = exc
    raise CritiqueParseError(
        f"critic reply is not a valid Critique: {last_exc}", raw=raw_critique
    ) from last_exc


def score(
    query: str,
    draft: str,
    *,
    critic: CriticPort,
    store: StorePort,
    retrieve_k: int = 5,
) -> PipelineResult:
    """Critique an existing draft. Does not call generate or revise."""
    retrieved_ids, critique = _critique_draft(
        query, draft, critic=critic, store=store, retrieve_k=retrieve_k
    )
    return PipelineResult(
        query=query,
        draft=draft,
        retrieved_ids=retrieved_ids,
        critique=critique,
        final="",
        shielded=True,
    )


def run(
    query: str,
    *,
    provider: Optional[object] = None,
    generator: Optional[GeneratorPort] = None,
    critic: Optional[CriticPort] = None,
    store: Optional[StorePort] = None,
    store_dir: Optional[Path] = None,
    shield: bool = True,
    retrieve_k: int = 5,
    draft: Optional[str] = None,
) -> PipelineResult:
    """Wald loop. `provider` may implement both LLM ports; calls stay separate."""
    del store_dir  # adapters construct the store; kept for call-site compatibility
    gen = generator or provider
    cri = critic or provider
    if draft is None:
        if gen is None:
            raise TypeError("run() requires generator= or provider=")
        text = gen.generate(query=query)
    else:
        text = draft
    if not shield:
        return PipelineResult(query=query, draft=text, final=text, shielded=False)
    if store is None:
        raise TypeError("run() requires store= when shield=True")
    if cri is None:
        raise TypeError("run() requires critic= or provider= when shield=True")
    if gen is None:
        raise TypeError("run() requires generator= or provider= when shield=True")
    retrieved_ids, critique = _critique_draft(
        query, text, critic=cri, store=store, retrieve_k=retrieve_k
    )
    if critique.survivorship_risk < LOW_RISK:
        return PipelineResult(
            query=query,
            draft=text,
            retrieved_ids=retrieved_ids,
            critique=critique,
            final=text,
            shielded=True,
        )
    revision = gen.revise(
        query=query,
        draft=text,
        critique_json=json.dumps(critique.model_dump(mode="json")),
    )
    return PipelineResult(
        query=query,
        draft=text,
        retrieved_ids=retrieved_ids,
        critique=critique,
        final=revision,
        shielded=True,
    )

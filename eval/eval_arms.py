# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Eval-only comparison arms. Not part of the Wald loop."""

from __future__ import annotations

import json

from absencecritic.domain.models import Critique, PipelineResult

# The cheapest alternative to the Wald critic: the same reviser, handed one
# fixed survivorship reminder for every query. No critic call, no store.
GENERIC_CAUTION = Critique(
    selection_filter=(
        "Not analysed. Generic reminder: the evidence behind the draft may be a "
        "sample of survivors."
    ),
    unknown_lethality=[
        "Cases that failed, dropped out, or were never recorded may be missing."
    ],
    survivorship_risk=0.5,
    confidence_adjustment="lower",
    caveats=["Check whether failures or unrecorded cases are missing before generalising."],
)

FIXTURE_NOTE = (
    "FixtureLLM.revise returns one recorded revision whatever critique it gets, "
    "so generic, critic_only, and shield share an answer. Arm deltas on fixtures "
    "are not a result; use a live provider."
)


def generic_arm(query: str, draft: str, *, generator) -> PipelineResult:
    """Revise the shared draft against GENERIC_CAUTION. critique stays None:
    there was no critic, so scoring uses the answer text only."""
    final = generator.revise(
        query=query,
        draft=draft,
        critique_json=json.dumps(GENERIC_CAUTION.model_dump(mode="json")),
    )
    return PipelineResult(query=query, draft=draft, final=final, shielded=False)

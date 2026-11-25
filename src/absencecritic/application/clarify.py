# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""A clarifying draft does not erase a filter the question already named."""

from __future__ import annotations

import re

from absencecritic.application.retrieve import query_names_selection
from absencecritic.domain.models import ConfidenceAdjustment, Critique

_MAX_WORDS = 30
_ASSERTS = re.compile(r"\b(should|works|proven|always|best|guaranteed)\b", re.I)
_CAVEAT = (
    "The question looks at a filtered record. Keep the clarifying question, "
    "and name what that record leaves out."
)


def draft_only_clarifies(draft: str) -> bool:
    text = " ".join(draft.split())
    if "?" not in text or len(text.split()) > _MAX_WORDS:
        return False
    return _ASSERTS.search(text) is None


def apply_filtered_clarification(query: str, draft: str, critique: Critique) -> Critique:
    """Raise a too-quiet report card when the question names a filter and the draft only asks which thing.

    How-to and plain-fact questions do not match, so a clarifying knot or sum stays quiet.
    """
    # Imported here so this module can load before loop finishes importing it.
    from absencecritic.application.loop import LOW_RISK

    if critique.survivorship_risk >= LOW_RISK:
        return critique
    if not draft_only_clarifies(draft) or not query_names_selection(query):
        return critique
    caveats = list(critique.caveats) or [_CAVEAT]
    return critique.model_copy(
        update={
            "survivorship_risk": LOW_RISK,
            "confidence_adjustment": ConfidenceAdjustment.seek_more_data,
            "caveats": caveats,
        }
    )

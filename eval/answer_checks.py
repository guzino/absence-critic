# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Checks on final answers shared by the eval and benchmark scorers."""

from __future__ import annotations

import re

# The user never sees a draft, critique, or store; final answers must not talk about them.
PIPELINE_LEAK_RE = re.compile(
    r"\b(the|this|your) draft\b|\brevised (version|answer|draft)\b|"
    r"\b(no|nothing)\s+(\S+\s+){0,2}retrieved\b|\bstore (hits?|entries)\b|"
    r"\bthe critique\b|\bwald module\b",
    re.I,
)


SURVIVORSHIP_CAVEAT_RE = re.compile(
    r"\bcaveat\b|visible sample|cannot show|survivor|base[- ]rates?|unpublished|"
    r"file[- ]drawer|did not return|never recorded|selection (filter|effect|bias)|"
    r"missing from (the|this) (sample|record|data)",
    re.I,
)


def leaks_pipeline(text: str | None) -> bool:
    return bool(PIPELINE_LEAK_RE.search(text or ""))


MAIN_EVAL_MISSING_DATA_RE = re.compile(
    r"surviv|missing|unpublished|base[- ]rates?|file[- ]drawer|unknown|caveat|"
    r"did not return|non-survivor|selection (filter|bias|effect|process)|"
    r"under[- ]represen|over[- ]represen|"
    r"under[- ]sampl|failure rate|without data|cannot reveal|visible sample|"
    r"no published evidence|held[- ]out validation|positive[- ]result bias|"
    r"never guaranteed|not guaranteed|guaranteed outcomes|"
    r"visible test|omit failed|learning opportun",
    re.I,
)


def mentions_missing_data(text: str | None) -> bool:
    """True when the answer names missing, filtered, or unpublished evidence."""
    return bool(MAIN_EVAL_MISSING_DATA_RE.search(text or ""))


def adds_unneeded_caveat(answer: str | None, draft: str | None = None) -> bool:
    """True when the answer carries more survivorship-caveat language than its draft.

    Only meaningful for questions labelled as not needing a caveat (controls).
    Without a draft, any caveat language counts.
    """
    added = len(SURVIVORSHIP_CAVEAT_RE.findall(answer or ""))
    return added > len(SURVIVORSHIP_CAVEAT_RE.findall(draft or ""))

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Eval-only cost metering. Wraps a provider; the Wald loop does not know about it."""

from __future__ import annotations

import time

COST_KEYS = ("calls", "prompt_tokens", "completion_tokens", "seconds")


def empty_cost() -> dict:
    return {key: 0 for key in COST_KEYS}


def add_cost(a: dict, b: dict) -> dict:
    out = {}
    for key in COST_KEYS:
        if a.get(key) is None or b.get(key) is None:
            out[key] = None
        else:
            out[key] = a[key] + b[key]
    return out


class MeteredProvider:
    """GeneratorPort and CriticPort substitute that times each call.

    Token counts come from the inner provider's ``usage`` totals when it has
    them (OpenAICompat does); otherwise they are None.
    """

    def __init__(self, inner) -> None:
        self.inner = inner
        self._spent = empty_cost()

    def take(self) -> dict:
        """Return the cost since the last take() and reset it."""
        spent, self._spent = self._spent, empty_cost()
        return spent

    def _metered(self, method, **kwargs) -> str:
        usage = getattr(self.inner, "usage", None)
        before = dict(usage) if isinstance(usage, dict) else None
        started = time.perf_counter()
        try:
            return method(**kwargs)
        finally:
            spent = {"calls": 1, "seconds": time.perf_counter() - started}
            for key in ("prompt_tokens", "completion_tokens"):
                spent[key] = (
                    usage[key] - before[key] if before is not None and key in usage else None
                )
            self._spent = add_cost(self._spent, spent)

    def generate(self, *, query: str) -> str:
        return self._metered(self.inner.generate, query=query)

    def critique(self, *, query: str, draft: str, store_hits: str) -> str:
        return self._metered(
            self.inner.critique, query=query, draft=draft, store_hits=store_hits
        )

    def revise(self, *, query: str, draft: str, critique_json: str) -> str:
        return self._metered(
            self.inner.revise, query=query, draft=draft, critique_json=critique_json
        )


def cost_summary(rows: list[dict], arms: tuple[str, ...]) -> dict:
    """Mean cost per question for each arm, overall and by query kind."""
    scored = [row for row in rows if "cost" in row]
    out: dict[str, dict] = {}
    for scope in ("all", "biased", "control"):
        picked = [r for r in scored if scope == "all" or r.get("kind") == scope]
        if not picked:
            continue
        out[scope] = {}
        for arm in arms:
            means = {}
            for key in COST_KEYS:
                values = [r["cost"][arm][key] for r in picked]
                means[key] = (
                    None if any(v is None for v in values) else round(sum(values) / len(values), 3)
                )
            out[scope][arm] = means
        base = out[scope][arms[0]]
        for arm in arms:
            tokens = _tokens(out[scope][arm])
            base_tokens = _tokens(base)
            out[scope][arm]["tokens_vs_baseline"] = (
                round(tokens / base_tokens, 2) if tokens is not None and base_tokens else None
            )
    return out


def _tokens(cost: dict) -> float | None:
    if cost["prompt_tokens"] is None or cost["completion_tokens"] is None:
        return None
    return cost["prompt_tokens"] + cost["completion_tokens"]

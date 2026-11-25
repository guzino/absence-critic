# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


def query_hash(query: str) -> str:
    return hashlib.sha256(query.strip().encode("utf-8")).hexdigest()[:16]


class FixtureQueryNotFound(KeyError):
    """The offline corpus has no recorded response for this query."""


class FixtureLLM:
    """Offline LLM implementing GeneratorPort and CriticPort."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._by_query: dict[str, dict[str, Any]] = {}
        self._by_hash: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw = raw.get("responses", [])
        if not isinstance(raw, list):
            raise ValueError(f"Expected a list of fixture responses in {self.path}")
        self._by_query.clear()
        self._by_hash.clear()
        for item in raw:
            q = str(item["query"]).strip()
            self._by_query[q] = item
            self._by_hash[query_hash(q)] = item

    def _lookup(self, query: str) -> dict[str, Any]:
        q = query.strip()
        item = self._by_query.get(q) or self._by_hash.get(query_hash(q))
        if item is None:
            raise FixtureQueryNotFound(
                f"No fixture for query {q!r} (hash {query_hash(q)}). "
                "Use --provider openai with OPENAI_API_KEY, or add a fixture."
            )
        return item

    def generate(self, *, query: str) -> str:
        return str(self._lookup(query)["draft"])

    def critique(self, *, query: str, draft: str, store_hits: str) -> str:
        del draft, store_hits
        critique = self._lookup(query)["critique"]
        if isinstance(critique, str):
            return critique
        return json.dumps(critique)

    def revise(self, *, query: str, draft: str, critique_json: str) -> str:
        del draft, critique_json
        return str(self._lookup(query)["revision"])

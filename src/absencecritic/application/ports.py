# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Protocol

from absencecritic.domain.models import StoreEntry


class GeneratorPort(Protocol):
    def generate(self, *, query: str) -> str:
        """Draft an answer. Must not receive store hits."""

    def revise(self, *, query: str, draft: str, critique_json: str) -> str:
        """Revise a draft from structured critique JSON only."""


class CriticPort(Protocol):
    def critique(self, *, query: str, draft: str, store_hits: str) -> str:
        """Return Critique JSON. This is the only LLM path that sees the store."""


class StorePort(Protocol):
    def retrieve(
        self, query: str, draft: str = "", k: int = 5
    ) -> list[tuple[StoreEntry, float]]:
        ...

    def format_hits(self, hits: list[tuple[StoreEntry, float]]) -> str:
        ...


class DesignGeneratorPort(Protocol):
    def expand(self, *, query: str, draft: str, critique_json: str) -> str:
        """Produce gap-directed designs from critique JSON. Must not receive store hits."""


class DesignCriticPort(Protocol):
    def score_designs(
        self, *, query: str, draft: str, critique_json: str, candidates: str
    ) -> str:
        """Return DesignScoreSheet JSON. Must not receive raw store hits."""

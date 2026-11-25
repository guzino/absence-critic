# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""StorePort adapter that ranks entries by embedding cosine similarity.

Wraps YamlStore so pending feedback and the nested private/ folder stay out.
The embedder is an adapter detail, not a new port, and WaldLoop is unchanged.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol

from absencecritic.adapters.store.yaml_store import YamlStore, retrievable
from absencecritic.domain.models import StoreEntry

# Paraphrases of the same note land well above this; unrelated text does not.
COSINE_FLOOR = 0.72


class MissingEmbedKey(RuntimeError):
    """OPENAI_API_KEY is required for the live embeddings endpoint."""


class EmbedError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class Embedder(Protocol):
    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per text, in the same order."""


def entry_text(entry: StoreEntry) -> str:
    return "\n".join(
        [
            entry.id,
            entry.domain,
            entry.selection_process,
            entry.survivor_pattern,
            entry.non_survivor_evidence,
            entry.provenance,
        ]
    )


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


class ScriptedEmbedder:
    """Test double: each group of exact strings shares one axis."""

    def __init__(self, groups: list[list[str]]):
        self.groups = groups

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    def _one(self, text: str) -> list[float]:
        vector = [0.0] * (len(self.groups) + 1)
        for index, group in enumerate(self.groups):
            if text in group:
                vector[index] = 1.0
                return vector
        vector[-1] = 1.0
        return vector


class HashEmbedder:
    """Offline bag-of-tokens embedder. Shared words rank together; paraphrases do not."""

    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    def _one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            slot = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[slot] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


class OpenAIEmbedder:
    """POST {base}/embeddings on an OpenAI-compatible server."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        *,
        timeout: float = 60.0,
        urlopen=None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.model = (
            model or os.environ.get("ABSENCECRITIC_EMBED_MODEL") or "text-embedding-3-small"
        )
        self.timeout = timeout
        self._urlopen = urlopen or urllib.request.urlopen
        if not self.api_key:
            raise MissingEmbedKey(
                "OPENAI_API_KEY is not set. Use --retrieve keyword, or set the key."
            )

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise EmbedError(
                "The embeddings request failed.", status=exc.code
            ) from exc
        except urllib.error.URLError as exc:
            raise EmbedError("The embeddings request failed.") from exc
        try:
            body = json.loads(raw.decode("utf-8"))
            rows = sorted(body["data"], key=lambda row: row["index"])
            vectors = [list(row["embedding"]) for row in rows]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise EmbedError("The embeddings reply was not usable.") from exc
        if len(vectors) != len(texts):
            raise EmbedError("The embeddings reply did not cover every input.")
        return vectors


class EmbeddingStore:
    def __init__(
        self,
        directory: Path,
        embedder: Embedder,
        *,
        floor: float = COSINE_FLOOR,
    ):
        self.inner = YamlStore(directory)
        self.embedder = embedder
        self.floor = floor
        self._cached_texts: list[str] | None = None
        self._entries: list[StoreEntry] = []
        self._vectors: list[list[float]] = []

    def retrieve(
        self, query: str, draft: str = "", k: int = 5
    ) -> list[tuple[StoreEntry, float]]:
        del draft  # The question is what gets embedded. The draft is for the critic.
        if k <= 0 or not query.strip():
            return []
        self._ensure_vectors()
        if not self._entries:
            return []
        query_vector = self.embedder.embed_many([query])[0]
        scored = []
        for entry, vector in zip(self._entries, self._vectors):
            score = cosine(query_vector, vector)
            if score >= self.floor:
                scored.append((entry, score))
        scored.sort(key=lambda item: (-item[1], item[0].id))
        return scored[:k]

    def format_hits(self, hits: list[tuple[StoreEntry, float]]) -> str:
        return self.inner.format_hits(hits)

    def _ensure_vectors(self) -> None:
        entries = [entry for entry in self.inner.entries if retrievable(entry)]
        texts = [entry_text(entry) for entry in entries]
        if texts == self._cached_texts:
            return
        self._entries = entries
        self._vectors = self.embedder.embed_many(texts)
        self._cached_texts = texts

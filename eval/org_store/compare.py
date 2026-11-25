# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Right-entry rate and off-topic hits for one store against a question list.

Run from the repo root:

    python eval/org_store/compare.py
    python eval/org_store/compare.py --retrieve hash
    python eval/org_store/compare.py --retrieve embedding
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from absencecritic.adapters.store.embedding import (  # noqa: E402
    EMBED_UPLOAD_WARNING,
    EmbeddingStore,
    HashEmbedder,
    OpenAIEmbedder,
)
from absencecritic.adapters.store.yaml_store import YamlStore  # noqa: E402

HERE = Path(__file__).resolve().parent


def retrieval_rates(store, items: list[dict]) -> dict:
    right = 0
    on_topic = 0
    off_topic = 0
    off_topic_hits = 0
    misses: list[str] = []
    queries = [item["query"] for item in items]
    if hasattr(store, "retrieve_many"):
        grouped = store.retrieve_many(queries, k=3)
    else:
        grouped = [store.retrieve(query, k=3) for query in queries]
    for item, hits in zip(items, grouped):
        ids = [entry.id for entry, _score in hits]
        if item.get("off_topic"):
            off_topic += 1
            if ids:
                off_topic_hits += 1
            continue
        on_topic += 1
        if item["entry"] in ids:
            right += 1
        else:
            misses.append(item["id"])
    return {
        "right": right,
        "on_topic": on_topic,
        "off_topic": off_topic,
        "off_topic_hits": off_topic_hits,
        "misses": misses,
    }


def _items() -> list[dict]:
    raw = yaml.safe_load((HERE / "paraphrases.yaml").read_text(encoding="utf-8"))
    paraphrases = list(raw["paraphrases"])
    off_topic = [{**item, "off_topic": True} for item in raw["off_topic"]]
    return paraphrases + off_topic


def _store(name: str):
    directory = HERE / "store"
    if name == "keyword":
        return YamlStore(directory)
    if name == "hash":
        return EmbeddingStore(directory, HashEmbedder())
    print(EMBED_UPLOAD_WARNING, file=sys.stderr)
    return EmbeddingStore(directory, OpenAIEmbedder())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare retrieval on the paraphrase list. "
            "keyword is the default. hash stays on this machine. "
            "embedding sends every store note to the embeddings endpoint. "
            "A scripted embedder, not this command, is what the tests use."
        )
    )
    parser.add_argument(
        "--retrieve",
        choices=("keyword", "hash", "embedding"),
        default="keyword",
        help="Which retriever to score (default: keyword)",
    )
    args = parser.parse_args(argv)
    report = retrieval_rates(_store(args.retrieve), _items())
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

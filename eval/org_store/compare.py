# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Right-entry rate and off-topic hits for one store against a question list."""

from __future__ import annotations


def retrieval_rates(store, items: list[dict]) -> dict:
    right = 0
    on_topic = 0
    off_topic = 0
    off_topic_hits = 0
    misses: list[str] = []
    for item in items:
        hits = [entry.id for entry, _score in store.retrieve(item["query"], k=3)]
        if item.get("off_topic"):
            off_topic += 1
            if hits:
                off_topic_hits += 1
            continue
        on_topic += 1
        if item["entry"] in hits:
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

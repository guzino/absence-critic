---
name: add-store-entry
description: Add a Non-Survivor Store YAML entry with required provenance and a retrieval smoke check. Use when adding store notes, failure memory, post-mortems, or data/non_survivors entries.
---

# Add store entry

1. Prefer `absencecritic ingest path/to/entries.yaml` or `absencecritic ingest --catalog path.yaml` (writes `ingested.yaml`). Or append by hand to [data/non_survivors/entries.yaml](../../../data/non_survivors/entries.yaml).
2. Required fields: `id`, `domain`, `selection_process`, `survivor_pattern`, `non_survivor_evidence`, `confidence`, `provenance`. Optional: `collection` (seed|catalog|feedback), `source_url`, `ingested_at`.
3. `provenance` is a real citation or `author prior, low confidence`. An author prior is tagged `evidence: author_prior`, shown to the critic as such, and capped at confidence 0.5. Prefer finding a citation over adding a prior.
4. Quote scalars that contain `:` or inner `"`.
5. Do not invent a specific unpublished event as fact.
6. Smoke: load `YamlStore` and `retrieve` a query that should rank this `id` in the top hits.
7. SPDX on new files. Do not change `WaldLoop` for a data add.

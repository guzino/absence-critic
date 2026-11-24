<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Phase 1 working plan: Persistent Failure Memory

**Status (2026-11-24):** slices A-F landed on `main` (PRs #6-#10). Two-pass critic was the optional D path and was not shipped. Leftovers that Document 04 still names (live crawlers, real ACL) stay out of this phase on purpose; they are restated as empty regions below, not as unfinished homework.

This is an **engineering working plan**, not an origin document. Conceptual spec remains [`docs/03-bulletproof-shield-design.md`](../docs/03-bulletproof-shield-design.md) and the phase list in [`docs/04-implementation-roadmap.md`](../docs/04-implementation-roadmap.md). Do not "improve" those files while executing this plan.

Policy: [`AGENTS.md`](../AGENTS.md). One concern per GitHub PR. CI stays fixture-only.

## Wald pass on the remaining work

**Selection filter:** Easy-to-ship YAML, CLIs, and keyword overlap show up in green CI. Silent failures (hallucinated post-mortems, retrieve hits on the word "Wald", private org logs committed to a public repo) do not.

**Visible (already on `main`):**
- `StoreEntry` already has domain, selection process, survivor pattern, evidence, confidence, provenance.
- Loop: draft -> retrieve (critic only) -> `Critique` JSON -> revise. Generator never reads the store.
- Keyword `YamlStore.retrieve`.
- Curated ingest: `absencecritic ingest path.yaml` -> `ingested.yaml`; duplicate ids rejected.
- Fixture eval 15/15; encoding tests; PRs required.

**Empty regions (this plan):**
- No collection / version fields, so seed, catalog, and feedback collapse into one pile.
- No automated extract that is safer than a human YAML file.
- No user-feedback path that cannot mint fake non-survivors.
- No access-control story except `--store` / `ABSENCECRITIC_STORE`.
- Retrieve runs **before** critique, unconditionally. Document 03 lists retrieve after empty regions. Queries *about* Wald still overlap store tokens.

**Unknown lethality:** We do not yet know whether a second critic call after extra retrieve is worth the cost, or whether retrieve precision plus a cheap heuristic is enough. Measure on the existing 15 eval queries (and live Grok once) before calling retrieve "done."

**Armor:** Do not scrape the live web in CI. Do not LLM-summarize HTML into "evidence." Do not pass store hits into `generate` or `revise`. Do not add LangChain/LangGraph/DSPy. Do not rewrite origin `docs/`.

## Target shape (SOLID)

Keep `StorePort` retrieve-only. Writes stay on the YAML adapter (`YamlStore.add`, catalog ingest, feedback queue). New backends implement ports. `WaldLoop` changes only when the retrieve/critique **contract** changes.

Invariant: **only `critique()` sees store text.** If retrieve runs twice, both results go to the critic, never to the generator.

| Slice | Layer | Touch `WaldLoop`? |
|-------|--------|-------------------|
| A Versioning | `domain/` + YAML load | no |
| B Catalog ingest | `adapters/store/` | no |
| C Retrieve precision | `adapters/store/` | no |
| D Risk-aware retrieve | `application/` (+ maybe retrieve kwargs) | yes, small and explicit |
| E Feedback queue | `adapters/` (+ optional domain flags) | no |
| F Private store | adapters/CLI docs + gitignore | no |

## Slice A -- Entry identity and versioning

**Why:** Without `collection` and ingest metadata, a bad auto-ingest cannot be rolled back or filtered.

**What:** Optional fields on `StoreEntry` (defaults so current YAML still loads):
- `collection`: `seed` | `catalog` | `feedback` (default `seed` when absent)
- `source_url`: optional string
- `ingested_at`: optional ISO-8601 timestamp

File header on `ingested.yaml` may record `schema_version: 1`. Do not rewrite seed ids in `entries.yaml` unless a later PR is explicitly about data.

**Not:** auth, encryption.

**PR:** `feat/store-entry-versioning`  
**Tests:** old YAML loads; new fields round-trip; `tests/test_text_encoding.py` still passes.

## Slice B -- Catalog ingest (honest "automated extraction")

**Why:** Document 04 wants extractors from post-mortem collections and replication trackers. The survivor-biased version is "scrape announced-shutdown lists and call that the failure distribution." The store already notes that filter (`cbinsights-postmortem-filter`).

**What:** Frozen catalog YAML/JSONL (in-repo fixture or user file), **not** HTTP in pytest.
Required per row: `id`, `domain`, `collection`, `source_url`, `selection_process`, `survivor_pattern`, `non_survivor_evidence`, `confidence`, `provenance`.
Mapper in `adapters/store/catalog.py` -> `StoreEntry` -> existing `add()`.
Reject missing URL or provenance. Do not invent rates absent from the source line.
One fixture catalog (2-3 rows) citing sources already in the seed (BLS, OSC 2015, Franco 2014). Do not duplicate seed ids.

**Not in Phase 1:** live crawlers, PDF parsers, "summarize this URL with the live model."

**PR:** `feat/store-catalog-ingest`  
**CLI:** `absencecritic ingest --catalog path.yaml` (thin; logic in the adapter).  
**Tests:** ingest into `tmp_path`; retrieve ranks the new id.

## Slice C -- Retrieve precision (no extra LLM call)

**Why:** "Prefer the store when risk is high" is the wrong first knob if retrieve is already noisy. Phase 0 live eval treated a Wald quote as high-risk because the query contained "survivorship."

**What:**
- Token overlap is not enough: require a domain or id token, or a minimum overlap count.
- Do not let method-tokens alone (`wald`, `survivorship`, `bias`) rank startup/medical notes unless the **draft** is giving survivor-only advice.
- Keep `retrieve_k` at 5 unless eval says otherwise.

**PR:** `feat/store-retrieve-precision`  
**Tests:**
- `What is 2+2?` -> no useful store hits.
- Startup query still ranks BLS/VC-class ids.
- `Quote Abraham Wald's survivorship-bias insight in one sentence.` does not rank `college-dropout-founder-myth` first.
- Fixture eval stays 15/15.

Ship C and look at control `survivorship_risk` before D.

## Slice D -- Risk-aware retrieve (loop contract; last among retrieval work)

Document 03 wants retrieve at checklist step 4. Document 04 wants the store preferred when survivorship risk is detected.

**Prefer first:** cheap application heuristic (biased-question cues, not an LLM). Low -> `k=0` or `k=1`; high -> `k=5`. Still one critic call. Generator never sees hits.

**Only if C + heuristic leave a hole:** two-pass critic. Draft -> light retrieve -> critique; if `survivorship_risk` is high and `suggested_queries` is non-empty, retrieve again, **second** `critique()`, then revise. Cost: +1-2 LLM calls. Second hit list still does not go to `generate` / `revise`.

**Forbidden:** stuffing extra hits into `revise()`.

**PR:** `feat/risk-aware-retrieve` after C has numbers.  
**Eval:** 12 biased cases still caveated; 3 controls still low risk; `two-plus-two` does not require store ids.

## Slice E -- User feedback that cannot mint ghosts

**Why:** "This answer ignored a known failure mode" is how org-specific silent failures enter the store. Unmoderated model-shaped feedback is a machine for fake non-survivors.

**What:**
- `absencecritic feedback` writes `feedback/pending.yaml` with `collection: feedback`, required provenance (user + timestamp + "not independently verified"), `confidence` capped (for example <= 0.4).
- Retrieve ignores pending rows until `status: accepted` or a human `ingest` promotion.
- Default retrieve: `seed` + `catalog` + accepted feedback only.

**PR:** `feat/store-feedback-queue`  
**Tests:** pending entries absent from `retrieve()`; accepted present; missing provenance fails.

## Slice F -- Access control (honest, small)

This repository is public. Git YAML is not an ACL.

- Public seed stays citable-only (existing rule).
- Private memory is another directory (`ABSENCECRITIC_STORE` / `--store`), never committed.
- Do not put patient-level, employer, or credentialed failure logs in `data/non_survivors/`.
- Optional gitignore for `data/non_survivors/private/`.
- No auth server in Phase 1.

**PR:** README/CONTRIBUTING note + gitignore; can ride with E if the diff stays small.

## Phase 1 done (measurable)

Not "we wrote more YAML."

- Catalog ingest can add a citable row without hand-editing `entries.yaml`.
- Feedback cannot change answers until accepted.
- Controls about Wald or arithmetic do not pick up startup notes.
- Biased queries still use missing-data language and `lower` / `seek_more_data` / `abstain` (fixture 15/15; live provider re-measured once, not in CI).
- Generator still never receives store hits (architecture-guard + tests).
- CI: pytest (including encoding) + fixture eval; still no live keys.

## PR order

1. A versioning (unblocks B and E)
2. B catalog ingest
3. C retrieve precision
4. E feedback queue (swap with D only if org logs are the immediate need)
5. D risk-aware retrieve (only if C leaves a hole)
6. F private-store note (tiny; may ride with E)

Do not combine B with D. Do not combine E with auto-accept.

## Critic armor on this plan

- Catalog ingest reproduces each collection's own filter. Keep `selection_process` text; do not claim "now we have all failures."
- Versioning without retrieve rules will not fix Wald-quote false hits.
- Two-pass critique can look more rigorous while only spending tokens. Ship C first.
- Feedback provenance "user said so" is not BLS. Cap confidence; keep it out of retrieve until accepted.

<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Phase 0 working plan: Minimal Viable Shield

**Status (2026-11-24):** shipped on `main`. This plan is a critic-minded record of what "done" meant, what Document 04 still names that we did not build, and which leftovers are Phase 1-3 rather than reopen-Phase-0.

Not an origin document. Spec remains Document 04 Phase 0 and Document 03 (checklist, store, integration modes). Do not rewrite those files while reading this.

Policy: [`AGENTS.md`](../AGENTS.md).

## Wald pass

**Selection filter:** A working two-call loop plus green fixture CI is easy to ship. Silent failures (store text in `generate`, invented post-mortems, live keys in GitHub Actions, a mega-prompt that "is" the shield) do not show up as pytest red.

**Visible (on `main`):**
- Ports-and-adapters: `domain/` models, `application/` `run()` Wald loop, `adapters/` LLM + YAML store + CLI, `prompts/` text only.
- Loop: `generate` (query only) -> `retrieve` (critic only) -> validate `Critique` -> `revise` (critique JSON only).
- `--no-shield` is Document 03 on-demand mode.
- Seed Non-Survivor Store as curated YAML with provenance.
- Fixture eval: 12 biased + 3 control queries; recorded triples in `eval/fixtures/responses.yaml`.
- Live OpenAI-compatible adapter exists; CI never calls it.
- Public API: `from absencecritic import run, Critique, StoreEntry, PipelineResult`.

**Empty regions (not Phase 0 bugs):**
- Retrieve is keyword overlap, not a failure-aware index. Fixed in Phase 1 C/D, not by embeddings-in-the-loop.
- Store has no collection/version/feedback story (Phase 1).
- No frozen critic-only gold JSONL and no small critic model (Phase 2).
- No critique-only judge mode, no preference export, no public benchmark, no org KB product (Phase 3).
- Seed is a few dozen notes, not "the failure distribution."

**Unknown lethality:** We do not know how much of the live-Grok 15/15 is prompt overfitting to `eval/queries.yaml`. Fixture 15/15 does not measure a new domain.

**Armor:**
- Do not collapse draft+critic into one prompt to "save a call."
- Do not pass store hits into `generate` or `revise`.
- Do not add LangChain/LangGraph/DSPy.
- Do not put `OPENAI_API_KEY` in CI.
- Do not invent non-survivor anecdotes when retrieve returns [].
- Do not reopen Phase 0 to add a vector database "because RAG." That is a new store adapter later, with the same port.

## Target shape (SOLID)

This phase defined the shape later phases must not break.

| Principle | Here |
|-----------|------|
| S | One Wald stage per call. CLI parses args; `run()` owns the loop. Prompts are files. |
| O | New LLM = `GeneratorPort` + `CriticPort`. New store = `StorePort`. |
| L | `FixtureLLM` and live adapters substitute. Critique still validates. Generate still takes no hits. |
| I | Do not add `store_hits` to `generate` to "simplify." |
| D | Application imports ports. Domain has no HTTP. |

## What shipped (historical slices; do not re-PR)

These already landed. Listed so a future agent does not "implement Phase 0" again.

1. Package + CLI + SPDX + Apache-2.0.
2. Domain `Critique` / `StoreEntry` / `PipelineResult`.
3. Linear `run()` loop.
4. YAML store retrieve + format_hits.
5. Fixture LLM + eval harness (full loop, not judge-only).
6. OpenAI-compatible adapter.
7. Hex layout, AGENTS.md, PR-only `main`, encoding tests (supporting, not in Document 04).

## Leftovers that look like Phase 0

| Hole | Why it is not a Phase 0 slice | Where it goes |
|------|-------------------------------|---------------|
| Embedding retrieve | Easy to look like "real RAG" while ranking more survivor text | New `StorePort` later; not required to close Phase 0 |
| Bigger seed | More YAML is not a better selection model | Phase 1 catalog + feedback |
| Live eval in CI | Keys, cost, flake, prompt leakage into GitHub logs | Manual, user-asked only |
| Judge-only API | Tempting to bolt onto `run()` as a flag that skips revise | Phase 3 A (loop contract) |
| Fine-tuned critic | Months of data; 15 fixtures are not a model | Phase 2 |

## Phase 0 done (measurable)

Already true on `main`:

- Fixture eval 15/15 with missing-data language on biased queries and no bogus abstention on the three controls.
- Architecture-guard: generate never receives store hits.
- CI: pytest + fixture eval; no live provider.
- `--no-shield` returns the draft as `final`.

Document 04 success criteria (caveats vs baseline, calibration, inspectable critiques, acceptable overhead) are **not** fully measured. Phase 0 only compared shielded vs `--no-shield` on a tiny set. Do not claim a published robustness result.

## Critic armor on this plan

- Recording fixtures from a live model and then scoring those fixtures is circular. It proves the scorer matches the recording, not that the shield works on a new question.
- A high-quality critic prompt can hide an empty store: the model recites Wald vocabulary without a citable non-survivor. Phase 1 is what makes retrieve honest; Phase 0 did not.
- Shipping hex folders is not the same as shipping the method. The method is the isolated critic plus structured output plus a store the generator cannot see.

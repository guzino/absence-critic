<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Phase 2 working plan: Specialized Critic Model

This is an **engineering working plan**, not an origin document. Conceptual spec remains Document 04 Phase 2 and Document 03 (critic as prompt, small model, or hybrid). Do not rewrite origin `docs/` while executing this plan.

Policy: [`AGENTS.md`](../AGENTS.md). One concern per GitHub PR. CI stays fixture-only: no GPU, no training, no live keys.

Phase 1 left a prompted critic, a retrieve heuristic, and 15 recorded loop triples. Phase 2 is a **dataset, then a substitute `CriticPort`**, not a new graph and not a replacement of the primary model.

## Wald pass on the remaining work

**Selection filter:** Exporting JSONL, adding a Hugging Face script, and declaring "we have a critic model" all look like Phase 2. Training on the eval set, treating live Grok dumps as gold, and swapping the default critic without a held-out number do not.

**Visible (already on `main`, plus in-flight gold freeze):**
- `Critique` JSON is the training target shape.
- Fixture triples: query, draft, critique, revision in `eval/fixtures/responses.yaml`.
- Prompted `CriticPort` (`critique(query, draft, store_hits) -> JSON`).
- `WaldLoop` does not care which class implements the port.
- Gold freeze (PR #11 if not yet merged): `eval/gold/critiques.jsonl` + `python eval/export_gold.py`.

**Empty regions:**
- No train / held-out split. The 15 fixture critiques *are* the eval. Fine-tuning on them and citing fixture 15/15 is leakage.
- No human-refine overlay. Fixture critiques are model-shaped, including whatever the recording model got wrong.
- Live Grok critiques are not gold. They are another prompted run.
- No `CriticPort` adapter that points at a local or fine-tuned endpoint without also dragging a training stack into `application/`.
- No decision rule for when the small model becomes default. Prompted critic remains default until that rule fires.
- Store hits in gold rows are whatever retrieve returned that day. A future retrieve change silently invalidates "gold" unless provenance is recorded.

**Unknown lethality:** We do not know whether a LoRA on tens of rows beats the prompt on a *new* biased question. Document 04 says "months." Fifteen rows are a schema freeze, not a specialist.

**Armor:**
- Do not invent gold critiques.
- Do not put store hits in `generate`.
- Do not collapse draft+critic.
- Do not add LangGraph.
- Do not run fine-tunes in GitHub Actions.
- Do not replace the prompted critic because a training loss went down.
- Do not SFT the *generator* in this phase (that is Phase 3 training signal, and even there the generator must not be taught the store as facts).

## Target shape (SOLID)

Keep `CriticPort` as the only swap point. `WaldLoop` changes only if critique input/output changes (it should not).

| Slice | Layer | Touch `WaldLoop`? |
|-------|--------|-------------------|
| A Gold freeze | `eval/` | no |
| B Split + provenance | `eval/` | no |
| C Human overlay | `eval/` (+ optional schema in eval only) | no |
| D Grow dataset | `eval/` + scripts; live calls optional, never CI | no |
| E Local critic adapter | `adapters/llm/` | no |
| F Train job | out of package / optional extra; not `domain/` | no |
| G Swap decision | eval + README default; adapter wiring only | no |

Same HTTP class may implement generate and critique; calls stay `generate` / `critique` / `revise`. A fine-tuned critic implements **`CriticPort` only** unless you have a separate generator checkpoint.

## Slice A -- Gold freeze (schema, not a model)

**Why:** Without a frozen, validating JSONL, every later notebook will scrape fixtures differently and silently drift.

**What:** `eval/gold/critiques.jsonl` from fixtures. Each `critique` object validates as `Critique`. Regenerator: `python eval/export_gold.py`. Record provenance (`eval/fixtures/responses.yaml`, query id, kind).

**Not:** human labels, train/test split (slice B), LoRA, changing the default provider.

**PR:** `feat/gold-critique-dataset` (PR #11).  
**Tests:** >=15 rows; biased and control present; regenerate matches the committed file; encoding tests pass.

## Slice B -- Split so eval cannot grade the training set

**Why:** The empty region in slice A. A specialist that memorizes 12 biased fixture critiques will look perfect and still fail the next startup question.

**What:**
- Partition gold into `train` and `heldout` (committed lists of query ids, not a random shuffle in CI).
- Held-out must include at least one biased and one control id.
- Fixture eval (`eval/queries.yaml`) stays the *product* regression. Training success is reported on held-out gold **and** on queries that were never in train.
- Document in this plan's "done" section: citing 15/15 after training on those 15 is a fail.

**Not:** adding 200 unlabeled live dumps and calling them held-out.

**PR:** `feat/gold-train-heldout`.  
**Tests:** exporter writes both files; no id in both; `test_gold` still regenerates the union.

## Slice C -- Human refine overlay

**Why:** Document 04: triples are "generated by strong models following the checklist and then human-refined." Unreviewed model JSON is a survivor of "what the prompted critic already says."

**What:** Optional overlay file (JSONL or YAML) keyed by query id. Overlay wins for training export. Fixtures stay the recording of the prompted system; do not silent-overwrite `responses.yaml` with human edits.
Each overlay row: editor, date, reason (what was wrong: hallucinated non-survivor, control over-flagged, missing empty region).

**Not:** using overlay to hide a loop bug. If the critic invents store ids, fix retrieve/prompt tests first.

**PR:** `feat/gold-human-overlay`.  
**Tests:** overlay id must exist in gold; missing provenance on an overlay row fails; fixture eval still 15/15 against *fixtures*, not overlay.

## Slice D -- Grow the dataset without poisoning it

**Why:** Tens of rows will not specialize a model. Growing by scraping the same 12 templates with paraphrases still overfits the template.

**What:**
- Script to log live runs to a **quarantine** JSONL (gitignored or `eval/gold/incoming/`, not mixed into train).
- Required fields: provider, model, date, query, draft, store hit ids, raw critique, parsed `Critique` or parse error.
- Promotion to train/heldout is a human PR (same overlay discipline).
- Prefer new query ids over paraphrases of `startup-launch`.

**Not:** auto-promoting live Grok to gold. Not downloading random HF "critique" corpora that are not Wald JSON.

**PR:** `feat/gold-incoming-log`.  
**Tests:** parser rejects rows that do not validate; incoming path is gitignored or fixture-only sample.

## Slice E -- Local critic adapter

**Why:** Open/closed: a fine-tuned endpoint is another adapter. If training code edits `WaldLoop`, the port was the wrong seam.

**What:** `adapters/llm/` class implementing `CriticPort` (and only that, unless it truly shares generate). Talks to a local OpenAI-compatible server or a specified model name. Fixture tests use a recorded local response or the existing `FixtureLLM` as stand-in.

**Not:** importing training libraries into `src/absencecritic`. Not changing `generate` signatures.

**PR:** `feat/local-critic-adapter`.  
**Tests:** substitute on `CriticPort`; `Critique.model_validate` still required; generate not given hits.

## Slice F -- Train job (outside CI)

**Why:** Document 04 wants a smaller/faster critic. The empty region is claiming that job belongs in the application core.

**What:** Optional extra (`scripts/` or a documented external recipe): read train JSONL, fine-tune LoRA or equivalent, emit an endpoint the slice E adapter can call. License and base-model attribution in the recipe. CPU-only smoke that *loads* a tiny dummy is allowed in pytest if it needs no download; full train is not.

**Not:** GitHub Actions GPU. Not a new pipeline stage. Not training the generator on critiques.

**PR:** `feat/critic-train-recipe` (docs + script only).  
**Tests:** JSONL schema the script expects matches `Critique`; dry-run fails on invalid JSON.

## Slice G -- Swap decision

**Why:** "Replace or augment the prompted LLM call" is a product default, not a merge of a notebook.

**What:** Default critic stays prompted until:
1. Held-out gold: structured fields match (risk band, `confidence_adjustment`, no invented store ids) at a bar written in the PR, not vibes.
2. Fixture eval still 15/15 with the new critic adapter wired in a **non-default** provider flag.
3. One live spot-check on biased + control (user-asked, not CI).
4. Controls still must not abstain.

Augment (prompted critic, small model as fallback) is allowed if both still go through `CriticPort` and one `Critique` object. Do not ensemble by concatenating two JSON blobs into `revise`.

**PR:** `feat/default-specialized-critic` only after 1-3.  
**Tests:** provider flag; default remains prompted until this PR explicitly flips it.

## Phase 2 done (measurable)

Not "we ran a LoRA."

- Frozen gold JSONL regenerates and validates.
- Train and held-out ids are disjoint; nobody reports train accuracy as the Phase 2 result.
- Overlay cannot silent-edit fixtures.
- Incoming live logs cannot enter train without a review PR.
- A local/fine-tuned critic is a `CriticPort` adapter.
- Prompted critic is still default unless slice G's checks passed.
- Generator still never receives store hits.
- CI: pytest + fixture eval; no GPU; no live keys.

## PR order

1. A gold freeze
2. B split
3. C overlay (can swap with D if incoming logs are the immediate need, but never skip B before F)
4. D incoming log
5. E adapter (can land before F using a stub endpoint)
6. F train recipe
7. G default swap (last)

Do not combine F with G. Do not combine A with F.

## Critic armor on this plan

- Gold that is only the prompted critic's own outputs teaches a student to imitate the teacher, including teacher mistakes (hallucinated hits, Wald-quote false alarms). Overlay and held-out new queries are the armor; more identical rows are not.
- A lower-latency critic that skips empty-region honesty is worse than the prompt. Measure invented `non_survivors` ids, not only token speed.
- Hybrid "rules + small model" is allowed by Document 03. Rules belong in `application/` or retrieve, not as a second hidden LLM call inside the adapter.
- Phase 3 will want preference pairs. Do not burn the generator by SFT-ing it on critic JSON in this phase so it "sounds Wald." That collapses the shield.

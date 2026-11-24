<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Phase 3 working plan: Deeper Integration

This is an **engineering working plan**, not an origin document. Conceptual spec remains Document 04 Phase 3 and Document 03 integration modes (evaluation harness, training signal) plus Document 02 (benchmarks as survivors, world models that imagine safe futures). Do not rewrite origin `docs/` while executing this plan.

Policy: [`AGENTS.md`](../AGENTS.md). One concern per GitHub PR. CI stays fixture-only.

Document 04 lists four bullets. They are **four tracks**, not one milestone. Each track can look complete while leaving the others empty. Do not merge a "Phase 3" PR that dumps training + benchmark + org SaaS together.

Phase 2 may still be in flight. Track A (judge mode) unblocks measuring Phase 2 swaps and Track B labels. Do not wait for a LoRA to start A.

## Wald pass on the remaining work

**Selection filter:** Demos, leaderboards, and "we export DPO JSON" are visible. Circular judges, teaching the primary model the store as fact, and a public benchmark built only from our 12 biased templates are not.

**Visible (prior phases):**
- Full loop with inspectable `Critique`.
- `--no-shield` baseline on the same query.
- Tiny eval (12 biased, 3 control) scoring missing-data language.
- Store ingest, catalog, pending feedback, private directory gitignore.
- `PipelineResult` already has draft, critique, final.

**Empty regions:**
- No critique-only API. You cannot score a foreign model output without also generating a new draft inside `run()`.
- No preference / contrastive export. Training-time use is a sentence in Document 04, not a file format.
- No trajectory/plan critique distinct from Q&A. Document 02's world-model hole is unaddressed; this repo is not a driving simulator and must not pretend to be one.
- No public benchmark with human labels separate from the critic-as-judge.
- No org product: private YAML is an access *hint*, not deployment.

**Unknown lethality:**
- Using AbsenceCritic as an automated judge to score AbsenceCritic will ratify its own vocabulary.
- Preference pairs of (draft, revised) can teach "add caveats" as style without teaching selection filters. Models then caveate arithmetic controls.
- Injecting "non-survivor trajectories" into a planner can become fictional accident fan-fiction (Document 03: do not invent lost planes).

**Armor:**
- Generator still never reads the store, including during training-data *construction* for the primary model. If a pair needs failure evidence, it is critic-side or human-side, not a system prompt dump of YAML into SFT.
- Do not invent detailed failure cases as training targets.
- Do not add LangGraph to "inject trajectories."
- Do not put org failure logs in the public seed.
- Do not claim Document 04 success criteria on 15 fixture rows.

## Target shape (SOLID)

| Track | Origin bullet | Layer | Touch `WaldLoop`? |
|-------|---------------|--------|-------------------|
| A Judge mode | Evaluation harness | `application/` + CLI thin flag | yes: stop after critique, or a sibling `score()` that shares ports |
| B Pair export | Training-time use | `eval/` + adapters logging | no |
| C Optional primary-model experiment | Training-time use | outside package / recipe | no |
| D Plan/trajectory critique | World-model extension | `prompts/` first; ports unchanged | no unless critique gains a field |
| E Public benchmark | Eval suite | `eval/` | no |
| F Org store | Organizational deployment | `adapters/store/` + docs | new `StorePort` only if YAML is the limit |

Do not add a mega-port "for integration." Judge mode still uses `CriticPort` + `StorePort` and must not call `generate` if the user already supplied a draft.

## Track A -- Evaluation harness (judge mode)

**Why:** Document 03 table: "Shield scores existing model outputs for survivorship risk." Today `run()` always drafts first, so you cannot judge a vendor dump.

**What:**
- Application function `score(query, draft, *, critic, store) -> PipelineResult` (or equivalent) that skips `generate` and `revise`. `final` stays empty or copies draft; `shielded` true; `critique` required.
- CLI: `--draft-file` / `--judge` (thin). Logic not in CLI.
- Fixture tests: no `generate` call; store still critic-only.

**Not:** changing `revise` to optionally no-op inside the same function with a boolean soup. Not scoring without validating `Critique`.

**PR:** `feat/critique-judge-mode`.  
**Tests:** spy/fake generator must not be called; control draft "2+2=4" stays low risk under fixtures; biased draft without caveats still high risk.

## Track B -- Preference and contrastive export

**Why:** Document 04: critiques become preference pairs or contrastive examples. The empty region is exporting *store text* as the chosen completion.

**What:**
- Export JSONL from logged runs: `prompt` = user query, `rejected` = unshielded draft, `chosen` = revised final, `critique` = structured JSON as metadata (not as the chosen string unless the task is "train a critic," which is Phase 2).
- Provenance: model ids, date, query id, whether overlay/human.
- Explicit license/use note: chosen text may still be wrong; pairs measure "shielded vs not," not truth.

**Not:** concatenating Non-Survivor Store entries into `chosen`. Not uploading pairs that contain private store rows.

**PR:** `feat/preference-pair-export`.  
**Tests:** exporter strips store body from pair fields; private collection rows never appear in public export fixtures.

## Track C -- Training-time experiment (outside CI)

**Why:** The origin bullet is real. Shipping a recipe is honest; shipping an unverified "robust model" is not.

**What:** External recipe (like Phase 2 F): DPO/contrastive on Track B pairs for a *primary* model checkpoint. Measure with Track E / fixture controls. If controls start abstaining, the experiment failed (style-caveat collapse).

**Not:** making that checkpoint the default `generate` in this repo without held-out numbers. Not continuing pre-training in CI.

**PR:** `feat/primary-preference-recipe`.  
**Tests:** schema only; no GPU.

## Track D -- Imagined futures (world-model analog, text only)

**Why:** Document 02/04: planners and world models imagine mostly benign futures because training trajectories survived. This repository can address **textual plans**, not vehicle simulation.

**What:**
- First: prompt wording in `prompts/` so when the query is a plan/trajectory ("walk me through a guaranteed product launch timeline"), empty regions include *paths not taken* and *attempts that would leave no write-up*.
- Store already has failure notes; retrieve remains critic-only.
- Optional later: `Critique` field only if eval shows the existing fields cannot hold trajectory holes. That is a domain PR with tests, not a side JSON key in the adapter.

**Not:** a physics engine. Not generating graphic accident stories as "non-survivor trajectories." Not a second loop graph. If a host system has its own planner, AbsenceCritic remains a critic call on the imagined plan string.

**PR:** `feat/plan-critique-prompt` then, only if needed, `feat/critique-trajectory-field`.  
**Tests:** a plan-like eval query still 15/15 overall; control Q&A unchanged; no new invented store ids required.

## Track E -- Survivorship eval suite

**Why:** Document 04: a benchmark that scores handling of survivor-biased questions, optionally with the shield as judge. Document 02: benchmarks are themselves survivors.

**What:**
- New held-out query set (`eval/benchmark/` or similar), **disjoint** from train gold and from the original 15 where possible.
- Human or frozen gold labels for: should caveate / should not abstain / must mention missing data. These labels are not the live critic's own JSON.
- Scorer: independent of "did the critic emit high risk?" Prefer lexical/structural checks plus optional *second* judge only if that judge is not the system under test.
- Publish format (YAML/JSONL) so others can run without our CLI.

**Not:** a leaderboard of who hedges more. Not using Track A judge as the only gold for the same critic.

**PR:** `feat/survivorship-benchmark`.  
**Tests:** ids disjoint from train lists; controls included; CI runs a *small* subset or the existing 15, not a huge live judge.

## Track F -- Organizational deployment

**Why:** Document 04: shield on internal knowledge bases. Phase 1 F already said git YAML is not an ACL.

**What:**
- Document the real deployment: `ABSENCECRITIC_STORE` on a private volume, feedback queue, accept step, no public commit.
- If YAML retrieve fails at org scale, a new `StorePort` (SQLite/fts, etc.) in `adapters/store/`. Same retrieve-only port. Pending feedback rules stay in the adapter or a thin application policy, not in the CLI.
- Optional: redact/export guard so `preference-pair-export` refuses `collection=feedback` unless a flag is set.

**Not:** multi-tenant auth server, SSO, or "AbsenceCritic Cloud" in this phase. Not putting credentialed logs in `data/non_survivors/entries.yaml`.

**PR:** `feat/org-store-adapter` only when a second backend exists; otherwise a docs slice may ride with Track B's private-export guard.

## Phase 3 done (measurable)

Phase 3 is **not** one checkbox. Each track has its own done:

| Track | Done means |
|-------|------------|
| A | Foreign draft in, `Critique` out, no `generate`. |
| B | Public export has pairs without store bodies. |
| C | Recipe exists; default generator unchanged until a measured PR. |
| D | Plan-like queries get empty-region language without fictional accidents; controls clean. |
| E | Held-out labeled set, disjoint ids, scorer that is not self-grading the critic under test. |
| F | Org can point a private store at a `StorePort` without committing secrets. |

Document 04 success criteria (more caveats than baseline, better calibration, inspectable shield, acceptable cost) are reported against Track E, not against fixture 15/15.

## PR order

1. A judge mode (unblocks honest scoring)
2. E benchmark skeleton (can start with a few labeled items)
3. B pair export
4. D plan prompt
5. F export guard / store adapter as needed
6. C primary-model recipe last among training work

Do not combine C with A. Do not combine E's labels with a critic self-score in the same PR as a "result."

## Critic armor on this plan

- Judge mode that still calls `generate` internally is not a harness; it is the old loop with extra flags.
- Preference pairs of (terse draft, hedged revision) will survive any selection filter: they look like alignment data. Controls in Track E are the holes in that armor.
- A public benchmark drawn only from startup/diet/dropout templates measures meme coverage, not missing-data reasoning in new domains.
- World-model language is a prestige empty region. Writing "inject non-survivor trajectories" in code comments without a textual plan critique is costume.
- Org deployment without pending-feedback discipline will mint ghost non-survivors at work scale (Phase 1 E, still binding).

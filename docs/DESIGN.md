<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Generative AbsenceCritic

**A design document, not a result.** Written against `absence-critic` at `e3403d4` (origin/main, after independent labels in #126). Nothing here is a measured finding.

The proposal extends the existing Wald loop. Today the critic asks what the *evidence* is missing and, when needed, revises an answer. In generative mode it asks what the *design space* is missing, and steers the model into those gaps. Document 03 already lists “abandoned-project descriptions” as Non-Survivor Store content; the shipped loop uses those notes only to caveat. This is the other half: invent in the gaps, without breaking the shield.

This is a working plan in the same sense as `plans/`, not an origin paper. It should not be copied into `docs/` unless a later PR is explicitly about those papers.

---

## 1. Motivation

A model trained on what was published, shipped, or saved learns the distribution of designs that survived long enough to be documented. Ask it for an e-bike, a settings screen, or a chair, and it usually reproduces the winners’ conventions: the battery in the frame, the tab bar at the bottom, the four-leg plan. That is the same “holes in the returning planes” problem the shield already targets, applied to a brief rather than a factual question.

A sticky-note prompt — “be creative,” “propose something unconventional” — is the analogue of the generic survivorship warning. It is cheap, and it sometimes works. It cannot tell a real gap from noise, and it has no memory of designs that were tried and killed, or of why they died, so it cannot notice when a blocker has expired (a cost that no longer applies, a material that now exists). The result is undirected novelty: surprising, often unusable, easy to confuse with progress.

Directed novelty is different. The model should name the filter that shaped the usual answers, retrieve failed or abandoned work and the reasons it died, and generate in those gaps, then check that the new work is still feasible and that it does not invent a fake history. Whether that beats “be creative” on usefulness is an open empirical question. This document specifies a prototype that can answer it on the same kind of protocol the repo already uses for the shield.

The shield result that makes this worth trying is precision, not eloquence: the critic stays quiet on ordinary questions and speaks when the evidence is survivor-filtered. Generative mode needs the same discipline. A brief that is a standard spec, a tight constraint, or a how-to should not be forced into a weird design.

---

## 2. Concept and loop

The generator still never reads the Non-Survivor Store. Only a critic does. Gap-directed generation is a revise-class call: it sees the brief, the draft, and structured critique JSON, never the notebook. That invariant does not expire in this mode (`AGENTS.md`).

```
Brief
  → generate()              # conventional draft; no store
  → retrieve(brief, draft)  # word matching, same StorePort
  → critique()              # design-filter critic → DesignCritique JSON
       │
       ├─ low risk, no gaps → return the draft, unforced
       ▼
  → expand()                # gap-directed designs from critique JSON only
  → score_designs()         # novelty / feasibility critic; no raw store
  → ranked designs + rationale
```

**Draft.** The primary model answers the brief as it does today (`GeneratorPort.generate`). The drafts will mostly look like successful, well-known designs. One draft is enough for the prototype.

**Survivor-filter critique.** A new prompt, not the current `critic.md`, runs the Wald checklist on a design space: the convention that made some designs visible; the usual solutions in the draft (`visible_damage`); the assumptions the draft takes as given; untried or abandoned regions, and why they are empty; and, of the retrieved hits, which dead or abandoned designs have a blocker the *store* marks as expired.

The critic uses only the provided hits. It must not invent a lapsed patent, a killed product, or a death reason, and it must not upgrade a hit’s `blocker_status` from `active` or `unknown` to `expired`. Hits with `evidence: author_prior` may name a convention, never a specific dead design presented as fact. If nothing relevant was retrieved, untried regions stay at the level of processes and conventions; those holes are marked unknown, not filled with anecdotes.

If `survivorship_risk` is below the existing `LOW_RISK` threshold (0.3 in `application/loop.py`) and both `untried_regions` and `revivable_entries` are empty, the loop returns the draft and does not call `expand`. That is the same quiet behavior the shield already has on fact and how-to questions.

**Retrieval and expired blockers.** Retrieval stays on `StorePort.retrieve(query, draft, k)` with the current word-matching backend. (`suggested_retrieve_k` may later need a design-brief cue so short briefs are not silently zeroed out.) The expired-blocker check is not a free-form model judgment. The curator sets `blocker_status` on the entry; the critic copies it. A revival is proposed only when status is `expired`. `unknown` stays unresolved; `active` is not revived. A wrong expiry is a store-quality bug, not something the model is invited to “correct.”

**Expand, score, rank.** `expand` is a new generator method with its own system prompt. It should produce a small set of designs (three is a reasonable default) that break a named assumption, explore an untried region, or revive a store-backed entry whose blocker has expired. Each design carries a short rationale that points at critique fields or store ids, not at “the store” or “the critique.” Historical claims are allowed only when the critique already contains that hit. Untried-region designs are labeled as hypotheses, not as recovered history.

A second, separate critic then scores each expanded design. It sees the brief, the draft, the critique JSON, and the candidates — not raw store hits — and returns structured scores: novelty, feasibility, usefulness, rationale quality, whether any source or dead design was invented, and a rank. Invented-source and invented-dead-design flags are hard gates.

The user-visible result is a ranked list of designs, each with a rationale. Pipeline talk stays hidden (`--show-critique` / JSON only). This is more LLM calls than the shield (draft, critique, expand, score, plus a retry on bad JSON). Cost should be metered with the existing usage path.

---

## 3. API and code changes

Keep the change backward compatible. The public shield API (`run`, `score`, `Critique`, `StoreEntry`, `PipelineResult`) and the default CLI path stay as they are. `application/loop.py` does not grow a `mode=` flag. `AGENTS.md` says that loop moves only when a port contract changes; this work is a new application function, new prompts, and optional schema additions.

**Function, ports, CLI.** Add `run_generative(...)` in a new module, `application/generative.py`, so shield tests and the layer table stay untouched. Export it later from `absencecritic` if the prototype lands; do not change the meaning of `run()`. Return a new `GenerativeResult` (brief, drafts, retrieved_ids, critique, candidates, scores, ranked, store-used flag). Do not overload `PipelineResult`.

Leave `GeneratorPort`, `CriticPort`, and `StorePort` as they are so `FixtureLLM` and `OpenAICompat` remain substitutes on the shield path. Add `DesignGeneratorPort.expand(*, query, draft, critique_json) -> str` and `DesignCriticPort.score_designs(*, query, draft, critique_json, candidates) -> str` (the latter returns `DesignScore` JSON). Do not add store parameters to `generate` or `expand`, and do not collapse draft + critic + expand into one prompt. JSON parse failures should reuse the existing one-retry behavior in `_critique_draft` (`CritiqueParseError`).

A thin CLI subcommand, for example `absencecritic design "…"`, plus `--no-store` (critic-only arm) and the existing `--provider` / `--store` / `--json` / `--show-critique`. Default `absencecritic "question"` remains the shield.

**Schemas.** Do not add required fields to `Critique`. Existing gold files, fixtures, and shield `model_validate` must keep working. Introduce a subclass:

```text
DesignCritique(Critique):
  assumptions: list[str]           # conventions the draft takes as given
  untried_regions: list[str]       # options never tried, or dropped early
  revivable_entries: list[RevivableHit]
```

`RevivableHit` carries `id`, `summary`, `provenance`, `confidence`, plus `death_reason`, `blocker`, `blocker_status`, and a short `revival_rationale`. The generative loop validates critic output as `DesignCritique`. The shield loop keeps validating as `Critique` (Pydantic will ignore unknown keys there, so a mixed reply cannot silently leak new fields into `revise`). Existing checklist fields keep their meaning: `selection_filter` is the convention filter, `visible_damage` is the usual designs in the draft, `empty_regions` remains the thin coverage map, `non_survivors` remains store-backed hits.

`DesignScore` is a new model, not a Critique variant: per-candidate 0–1 scores for novelty, feasibility, usefulness, and rationale quality; booleans for `invented_source` and `invented_dead_design`; a rank; a one-sentence rationale. A candidate that invents a source or a dead design is ineligible for the top rank.

**Prompts and store fields.** New files under `src/absencecritic/prompts/`: `critic_design.md` (same “use only store hits / do not invent / author_prior is not a rate” rules as `critic.md`), `expand.md` (gap-directed generation from critique JSON; no pipeline talk in the user-visible text), and `score_design.md`. Do not edit `draft.md`, `critic.md`, or `revise.md` unless a tiny, tested clarification is unavoidable.

Add optional fields on `StoreEntry`, all defaulting to `None`, so today’s YAML keeps loading:

| Field | Purpose |
|-------|---------|
| `kind` | `evidence` (default, today’s entries) or `design_failure` |
| `death_reason` | Why the design or product died or was abandoned |
| `blocker` | The concrete constraint that killed or prevented it |
| `blocker_status` | `active`, `expired`, or `unknown` |
| `event_date` | ISO date or year of abandonment, lapse, or kill, when known |

`domain`, `provenance`, and `source_url` already exist; do not add a second `source` field that duplicates them. The `author_prior` rule is unchanged: provenance starting with `"author prior"` is tagged `evidence: author_prior`, and `YamlStore.add` still rejects confidence above `MAX_AUTHOR_PRIOR_CONFIDENCE` (0.5). `format_hits` should append the new fields only when they are set. Ingest, catalog, and feedback stay as they are; catalog entries still require `source_url`.

**Tests.** Schema round-trips and optional-field defaults in `tests/test_schemas.py`. Architecture guards: `expand` is not passed store hits; only the critic calls `retrieve`. A fixture path with recorded draft / critique / expand / scores, and a fixture eval that CI can run without an API key. A post-check that every `revivable_entries` id was actually retrieved and that `blocker_status` was not upgraded. No live calls in CI.

---

## 4. Store

The public seed today (`data/non_survivors/entries.yaml`, 26 notes) covers startups, scientific literature, medical examples, model evaluation, hiring, and everyday reasoning. It has no design-failure entries. Generative mode is empty without them. Seed lightly, and only with the same provenance rules as the rest of the store.

**What may go in.** Lapsed or expired patents, only with an official identifier, a cited status, and `source_url` to the office record. `event_date` is the lapse or expiry date; `death_reason` / `blocker` must come from the record or a cited source, not from a guessed “why it failed.” A lapsed patent is a historical datapoint, not permission to practice the invention, and the store is not a freedom-to-operate opinion. Abandoned or recalled products from company announcements, official recalls, or serious cited reporting, with the product, the year, and the stated reason when the source states one — do not infer a secret internal reason. Killed internal projects belong in a private organizational store, the same way `eval/org_store` already handles private facts: a separate folder, not committed to the public repo, pending until a person accepts them (`absencecritic feedback`). They are likely the highest-value seed for a real team, and the easiest to get wrong in public.

**What must not go in.** An invented dead design, an unsourced cancellation, or a reconstructed failure anecdote. Author priors used as fake case studies: an author prior may say “consumer devices usually hide the battery in the chassis; alternatives are rarely shipped,” at confidence ≤ 0.5, but it may not invent a product name, a patent number, or a kill date. Scraping the live web inside CI or tests, then calling the result “the abandoned design space” (already forbidden in the roadmap). Patient-level data, employer logs, or another company’s confidential kill list in the public seed.

Start with a handful of well-cited public entries in the two prototype domains, plus, if a willing team exists, a private folder of their own killed work. Retrieval stays word matching on purpose. A vector index of “similar failed designs” is a later store adapter, and only if word matching fails; it still has to be critic-only. Mark `blocker_status` as `expired` only when the source shows the original constraint no longer holds, or when a curator with domain knowledge records that judgment in provenance. When unsure, use `unknown`. Wrong expiries will leak into revivals.

---

## 5. Prototype evaluation

This is a new benchmark, not an extension of the 38 survivorship questions. Those items test caveats, not design briefs, and must not be reused here as training or eval data.

**Domains and briefs.** Pick two and stay there: (1) product or industrial design, (2) software or UX patterns. Both have strong survivor conventions and a public record of abandoned attempts. Drug or molecule design is out of scope for a first prototype (safety, IP, and specialist review). Write about 15–20 frozen briefs before any live run, with none of the store’s entry text pasted into the brief, and hold out a few from prompt iteration. Each brief should state the goal, the hard constraints, and what “useful” means. Freeze the known-designs list and the success criteria before anyone sees model outputs.

**Arms** (share one draft per brief and sample, as `eval/benchmark/run.py` already does). Three samples per brief. CI runs fixtures only.

| Arm | What it is |
|-----|------------|
| `baseline` | `generate` only. The conventional answer. |
| `creative` | A “be creative / unconventional” system prompt. No critic, no store. The sticky-note control. |
| `critic_only` | Filter critique and expand, retrieve disabled (`k=0` or empty store). No revival of stored dead designs. |
| `shield` (critic + store) | The full `run_generative` loop. |

**Metrics.** Pre-register the operationalization, then do not change it after the first live answers exist.

- **Novelty.** Embedding distance from the candidate to a frozen “known designs” set for that brief (curated references, not a live web search), plus a judge score. Distance alone will reward nonsense; it is never a sufficient statistic.
- **Feasibility.** Judge (and, for a subset, a person) whether the design can work under the brief’s constraints with current, ordinary techniques. Not “possible in fifty years.”
- **Usefulness.** Does it actually serve the brief, not just differ from the baseline?
- **Rationale quality.** Does the rationale name a real filter, an untried region, or a store-backed expired blocker?
- **Invented-source rate.** Share of candidates that cite a patent, product, project, paper, or statistic that is not in the critique hits and not in a frozen public reference list. Also count invented *dead designs*, the analogue of `no_invented_sources` in `eval/benchmark/judge.md`.

Meter tokens and latency per arm. Generative mode will cost more than baseline and at least as much as the shield; cost is a decision input, not a footnote.

**Judges.** An independent cross-family rubric judge (different model family from the writer), wired the same way as `ABSENCECRITIC_JUDGE_*`, plus a blind human rating on a subset (or all, if 15–20 briefs stay small). Raters see the brief and the designs without arm names. At least one rater should not have written the briefs or the store. If the judge and the humans diverge on novelty or feasibility, trust the humans for the go/no-go and say so.

**Go / no-go.** Lock the margins in a short pre-registration note before the live run. The figures below are starting proposals, not findings. A go requires all of the following, on the frozen split, with the independent judge, and with no contradiction from the human subset:

1. Invented-source and invented-dead-design rates for `critic_only` and `shield` are no higher than `baseline` (ideally near zero on `shield`).
2. Mean feasibility of `shield` is not materially worse than `baseline` (for example no more than 0.10 on a 0–1 scale).
3. Novelty of `shield` is higher than `baseline` and at least as high as `creative`.
4. Usefulness of `shield` is at least as high as `creative`, and not materially worse than `baseline` under the same pre-registered margin.
5. Rationale quality is higher for `shield` than for `creative`, and `shield` beats `critic_only` on correct use of stored expired blockers (cited, not invented) when such entries are relevant.

No-go if any of those fail, or if humans consistently prefer `creative` on usefulness, or if a spot-check finds the loop citing dead designs that were not retrieved. A go is permission to write up the prototype and consider a larger eval. It is not a claim that labs should change a core model, or that the shield’s caveat results transfer to design.

Unknowns this document does not pre-settle: whether directed novelty is more useful than “be creative”; whether a small public design-failure store is enough, or only private kill-lists move the `shield` arm; whether the novelty critic just learns the writer’s style; whether expired-blocker labels are reliable enough to use at all.

---

## 6. Risks

**Novelty without value.** The loop can optimize for distance from known designs and produce unused oddities. Feasibility, usefulness, and the rule that low-risk briefs stay conventional are the counterweight. If those metrics are weak or gamed, call the prototype a failure, not “creative.”

**Hallucinated dead designs.** A fake lapsed patent or a fake killed product can look like research. Mitigations already in the architecture: the generator never sees the store; expand may state historical facts only from critique hits; author priors cannot supply specific cases; the score critic flags invented sources and invented dead designs as hard gates; a post-check that every cited id was actually retrieved. Residual risk remains, especially under `critic_only`, where the model may fill empty regions with plausible fiction. Those must be labeled as hypotheses.

**IP and patents.** A public store of lapsed patents, or a model that “revives” them, can be read as legal advice or as help around existing rights. It is not. Status changes, family members, and jurisdiction are easy to get wrong. The prototype should disclose that outputs are experimental design sketches, cite only office-backed records, and avoid any phrasing that a design is cleared for use. Internal killed-project notes stay private. If a domain cannot be seeded without legal review (for example active pharmaceutical matter), drop the domain.

**Judge bias and cost.** A model judge may reward fluent strangeness, fluent conservatism, or its own family’s taste. That is why the judge is cross-family and why a blind human rating is part of the go/no-go. Novelty embeddings reward residual error and do not get a veto. Four model stages, retries, three samples, and a judge will dwarf a single “be creative” call; if the full loop cannot beat that cheaper arm on usefulness and invented-source rate, cost alone is a reason to stop.

**Store errors and scope.** Word matching will miss relevant dead designs and sometimes pull the wrong domain. Wrong `blocker_status` will propose a revival that is still blocked. Treat those as eval failure modes, not as reasons to switch on a web crawl or to let the critic overwrite status. This mode does not replace the shield, does not fine-tune a core model, and does not rewrite origin `docs/`. A successful prototype is still a prototype.

---

## 7. Phased roadmap and issues

Build in slices that can land as their own pull requests, fixtures first, live runs only when requested. The build order for agents is `plans/generative.md`. Do not open these issues or PRs from this document; they are a filing list.

- **Phase A — Schema, no live models.** Optional `StoreEntry` fields and `DesignCritique` / `RevivableHit` / `DesignScore` / `GenerativeResult`. Tests for defaults, author-prior cap, and `format_hits`. Shield fixtures still pass unchanged.
- **Phase B — Loop and prompts, fixture-only.** `run_generative`, the three new prompts, the two new ports, CLI `design` subcommand, recorded fixture transcripts, architecture-guard coverage. Quiet behavior on a low-risk brief is tested.
- **Phase C — Seed and provenance.** A small public design-failure YAML for the two prototype domains, cited entries only; documentation of `blocker_status` and the IP disclaimer. No confidential seeds in git.
- **Phase D — Eval harness.** Frozen briefs, known-designs reference set, arms, metrics, judge rubric, embedding helper, fixture eval in CI. Pre-registration of the go/no-go margins, committed before any live answers.
- **Phase E — Live prototype, then decide.** A requested live run with a cross-family judge, a blind human rating, and a short write-up that reports go or no-go honestly. The public roadmap may name this earlier as the next experiment. That mention is a plan, not a finding. Describe it as a result only after this write-up.

### Issues the user could file

1. **Generative mode: backward-compatible schema for DesignCritique and design-failure store fields.** Optional `StoreEntry` fields (`kind`, `death_reason`, `blocker`, `blocker_status`, `event_date`) and a `DesignCritique` subclass (`assumptions`, `untried_regions`, `revivable_entries`) so existing shield fixtures and gold critiques stay valid.

2. **Generative mode: prompts for the design-filter critic, expand, and the novelty/feasibility critic.** New prompt files only; do not retune `critic.md` or `revise.md`. Encode the rules: no invented dead designs, no flipping `blocker_status`, author priors are not case studies.

3. **Generative mode: `run_generative` loop, ports, and CLI `design` subcommand.** New application module and result type; `expand` and `score_designs` ports; generator still never receives store hits; low-risk briefs return the draft unforced.

4. **Generative mode: fixture transcripts and CI path.** Record draft, critique, expand, and scores for a few briefs, including a low-risk control, so pytest and a fixture eval run without API keys.

5. **Seed cited design-failure entries for two prototype domains.** A small public YAML of lapsed-patent or abandoned-product notes with real provenance and conservative `blocker_status`. No invented cases; no confidential kill lists.

6. **Document provenance, expired-blocker, and IP rules for design-failure notes.** How to mark `expired` vs `unknown`, the author-prior cap, and a clear statement that revival sketches are not legal clearance.

7. **Enforce that revivable entries must match retrieved hits and store `blocker_status`.** Post-validate critic JSON: unknown ids dropped or rejected; status cannot be upgraded to `expired` by the model.

8. **Generative eval: frozen briefs, known-designs lists, and four arms.** About 15–20 briefs in product/industrial design and software/UX; arms `baseline`, `creative`, `critic_only`, and `shield`; three samples; shared drafts.

9. **Generative eval: judge rubric, embedding novelty, and invented-source metric.** Cross-family judge; 0–1 scores for novelty, feasibility, usefulness, rationale quality; hard flags for invented sources and invented dead designs; a frozen reference set for embeddings.

10. **Pre-register go/no-go criteria before the first live generative run.** Commit the margins and the human-rating plan first, including at least one rater who did not write the briefs or the store.

11. **Blind human rating protocol for generative designs.** Arm-blind presentation, instructions, and a script to compare human ranks with the judge. Humans break ties on the go/no-go if they disagree with the model judge.

12. **Meter tokens and latency for generative arms.** Extend the existing usage logging so a live run can compare cost against baseline and against the “be creative” arm, not only quality scores.

The success of this project is still the shield: speak only when the evidence is survivor-filtered, and bring in a team’s own missing cases. Generative mode is worth a careful prototype because the same missing cases might also be a source of new work. It is not worth bending the invariant, inventing a store, or claiming a result that has not been measured.

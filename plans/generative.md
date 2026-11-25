<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Generative design working plan

**Status (2026-11-25):** slices A-D shipped as engineering. Slice E (live run) is not done and needs an explicit ask. No finding. The spec is [`docs/05-generative-absencecritic.md`](../docs/05-generative-absencecritic.md). This file is the build order. Do not treat either file as a result.

The question: the shield already asks what evidence is missing from an answer. Generative mode asks what the design space is missing from a brief, then steers new designs into those gaps. Product and industrial design, and software or UX patterns, are the only two domains. Drug and molecule design stay out.

Policy: [`AGENTS.md`](../AGENTS.md). One concern per GitHub PR. CI stays fixture-only. Do not open the filing list in `docs/05-generative-absencecritic.md` section 7 as issues until a slice is actually ready to build. Origin documents 00-04 stay frozen.

## Wald pass

**Selection filter:** A "be creative" prompt, and a story about abandoned designs, are easy to ship and easy to confuse with a method. The hole is whether directed gaps are more useful than that sticky note, without inventing a dead product.

**Visible (on `main`):**
- Shield loop: `generate` (no store) then `retrieve` (critic only) then validated `Critique` then `revise` (critique JSON only).
- Low risk (below 0.3) returns the draft and skips revise.
- Store notes require provenance. Author priors are capped. Pending feedback and a nested `private/` folder stay out of retrieval.
- Keyword retrieval is the default. An embedding store adapter exists only as a separate lookup plug; it is not this mode.
- Public benchmark labels and the shield eval are about caveats, not design briefs. They must not be reused here as train or eval data.

**Empty regions:**
- No `DesignCritique`, `DesignScore`, or `GenerativeResult`.
- No design-filter critic, expand prompt, or novelty/feasibility critic.
- No design-failure fields on store entries (`kind`, `death_reason`, `blocker`, `blocker_status`, `event_date`).
- No public seed of cited abandoned designs.
- No frozen briefs, known-designs list, arms, or pre-registered go/no-go.

**Unknown lethality:**
- Directed novelty may be less useful than "be creative."
- A small public store may not move the full loop. Only a team's private kill-list might, and that list must not be committed.
- A novelty judge may reward strange prose. Humans break the tie.
- A wrong `blocker_status` revives a design that is still blocked.

**Armor:**
- The generator never reads the store. `expand` is a revise-class call: brief, draft, and critique JSON only.
- Do not edit `WaldLoop` or add `mode=` to `run()`. New function: `application/generative.py`.
- Do not add required fields to `Critique`. Do not retune `critic.md` or `revise.md` for this mode.
- Do not invent a lapsed patent, a killed product, or a death reason. Author priors may name a convention. They may not name a product, a patent number, or a kill date.
- The model does not upgrade `blocker_status` to `expired`. The curator sets it.
- Do not scrape the live web in CI and call that the abandoned design space.
- A revival sketch is not legal clearance and not a freedom-to-operate opinion.
- Do not claim the shield's caveat numbers transfer to design.

## Target shape (SOLID)

| Piece | Layer | Touch `WaldLoop`? |
|-------|--------|-------------------|
| Optional store fields, `DesignCritique`, `DesignScore`, `GenerativeResult` | `domain/` | no |
| `run_generative` | `application/generative.py` | no. New ports `expand` and `score_designs`, not new parameters on `generate` |
| `critic_design.md`, `expand.md`, `score_design.md` | `prompts/` | no |
| `absencecritic design` subcommand | `adapters/cli/` | no. Thin. Default `absencecritic "question"` stays the shield |
| Design-failure YAML | `data/` or `eval/` seed, cited only | no |
| Briefs, arms, judge, pre-registration | `eval/` | no |

`FixtureLLM` and the live adapter stay substitutes on the shield path. Do not collapse draft, critic, and expand into one prompt.

## Slice A. Schema, no live models

**What:** Optional `StoreEntry` fields, all defaulting to empty so today's YAML still loads. `DesignCritique` subclasses `Critique` with `assumptions`, `untried_regions`, and `revivable_entries`. `DesignScore` and `GenerativeResult` are new models. `format_hits` prints the new fields only when they are set. Author-prior cap stays.

**Not:** a loop, a prompt edit, a seed entry, a CLI flag.

**Done:** schema tests pass, and the existing shield fixture eval still passes with no prompt or loop diff.

## Slice B. Loop, prompts, fixture path

**What:** `run_generative` in `application/generative.py`. Three new prompts. Ports `expand` and `score_designs`. CLI subcommand `design`, plus `--no-store` for the critic-only arm. Recorded fixture transcripts for a few briefs, including one low-risk brief that returns the draft and does not call expand. Post-check: every revivable id was retrieved, and `blocker_status` was not upgraded.

**Not:** live API calls. Not changing `run()`. Not seeding the public store in the same PR.

**Done:** pytest and a fixture eval run with no API key. Architecture guard: expand is not passed store hits. Only the critic calls retrieve.

## Slice C. Cited seed and the rules in writing

**What:** A handful of public design-failure notes in the two domains. Each has a real source, a `source_url` when it is a catalog-style record, and a conservative `blocker_status` (`unknown` when unsure). A short note on how to mark `expired`, the author-prior cap, and the IP disclaimer.

**Not:** confidential kill lists. Not invented cases. Not a web crawl. Not private employer logs in git.

**Done:** every new entry has provenance a reader can check. Retrieval still uses the existing store port.

## Slice D. Frozen eval, before any live answer

**What:** About 15 to 20 briefs, goal plus hard constraints plus what "useful" means. A frozen known-designs list per brief. Arms: `baseline`, `creative` ("be creative", no store), `critic_only` (no retrieval), `shield` (full loop). Three samples. Shared draft per brief and sample. Judge rubric and invented-source metric specified. Go/no-go margins written down in the repo before the first live answer exists. At least one human rater must be someone who did not write the briefs or the store.

**Not:** changing the margins after seeing live answers. Not reusing the 38 survivorship questions. Not a live run in this slice.

**Done:** fixture eval of the harness is in CI. The pre-registration file is committed and dated.

## Slice E. Live run, only when asked

**What:** One requested live run. Cross-family judge. Blind human rating on a subset. A short write-up that says go or no-go. Cost and latency per arm are part of the decision.

**Go requires all of these on the frozen split:** invented sources and invented dead designs no worse than baseline; feasibility not materially worse than baseline; novelty above baseline and at least as high as "be creative"; usefulness at least as high as "be creative" and not materially worse than baseline; rationale quality above "be creative"; stored expired blockers cited, not invented.

**No-go** if any of those fail, if the human raters prefer "be creative" on usefulness, or if a spot-check finds a cited dead design that was not retrieved. A go is permission to write up the prototype. It is not a claim that a lab should change a core model.

**Not:** turning generative mode on by default. Not mentioning it on the wiki as a result before this write-up.

## Critic armor on this plan

This plan can look complete while the only thing that shipped is a schema. Slice A without B is not a generative mode. A fixture transcript is not a finding. A public patent note is not evidence the loop beats "be creative." Stop at the first failed gate. Do not fill the hole with a more fluent prompt.

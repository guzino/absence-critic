<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Changelog

## Unreleased

### Fixed

- A clarifying draft still gets one caveat when the question names a filtered record (the literature, published studies, famous cases, what survived). How-to and fact questions that only share a retrieval word such as "score", "published", or "based on" stay quiet.

### Added

- `--retrieve embedding` ranks store notes by cosine similarity. It sends the question and the full text of every store note to the embeddings endpoint. `ABSENCECRITIC_EMBED_API_KEY`, `ABSENCECRITIC_EMBED_BASE_URL`, and `ABSENCECRITIC_EMBED_MODEL` choose that endpoint; otherwise the chat key and URL are used. `--retrieve hash` stays on the machine and only matches shared words. The 0.72 cutoff is unmeasured, and the paraphrase tests use a scripted embedder.

## 0.1.5 - 2026-11-25

Eval, hardening, and published multi-model findings. Package API and prompts are unchanged from 0.1.4 except the critic-call retry.

### Changed

- Critic calls retry once when the reply is not valid Critique JSON (helps open-weight models).

### Eval

- Benchmark judge plumbing: `ABSENCECRITIC_JUDGE_*` env vars, `judge_client()`, `--samples` on `eval/benchmark/run.py`, and `sample_spread` / `judge_model` on `eval/benchmark/score.py`.
- `mentions_missing_data()` in `eval/answer_checks.py` centralises main-eval missing-data wording ([#107](https://github.com/guzino/absence-critic/issues/107)).
- Biased main-eval pass accepts `confidence_adjustment: unchanged` when the answer still names missing data.
- Benchmark and org-store runners record arm errors (bad critic JSON) and continue ([#120](https://github.com/guzino/absence-critic/pull/120), [#121](https://github.com/guzino/absence-critic/pull/121)).
- Aggregate score JSON and answer JSONL for published runs live under `eval/benchmark/artifacts/` (no per-answer cases in `*.score.json`).

### Findings

- Independent judge (`gpt-4.1-mini`) on Grok answers: shield and critic_only beat the generic reminder; shield 0 control false alarms vs 34/36 for generic ([#106](https://github.com/guzino/absence-critic/issues/106)).
- Second answering model `openai/gpt-4o-mini`: critic arms still quiet on controls; sticky note can beat critic_only on overall rubric; store lift larger than on Grok ([#109](https://github.com/guzino/absence-critic/issues/109)).
- Open-weight `meta-llama/llama-3.3-70b-instruct` judged by Grok (cross-family): shield pass 0.94 std / 0.83 hard; concrete evidence 0.27 with store vs 0.04 without; org-store shield fact rate 0.75.

## 0.1.4 - 2026-11-25

### Changed

- When the critic rates survivorship risk below 0.3, the loop returns the draft as the answer and skips the revise call. The critique is still returned. This removes unneeded caveats and saves a model call on low-risk questions.
- The critic no longer treats how-to, procedural, recipe, grammar, or style questions as survivor-filtered unless the draft generalises from success stories. A caveat needs a nameable process that removed failed cases from view.

### Eval

- `eval/run_eval.py` reports `cost_by_arm`: calls, prompt and completion tokens, and seconds per question for each arm, overall and by biased and control. `OpenAICompat` keeps running usage totals from the provider's `usage` field.
- 12 hard benchmark items (`difficulty: hard`): biased questions that do not name the filter, and how-to controls that need no caveat. The score report gains `by_difficulty`. Labels are agent-drafted and not independent.

### Findings

On grok-4-fast-non-reasoning, the hard how-to controls showed the critic inventing caveats (3 of 4 without the store, 2 of 4 with it). After this release both critic arms are at 0 of 4 and pass 12 of 12 hard items, and the shield's cost on control questions drops from about 8 to 6 times the plain answer's tokens. Trade-off: when the critic without a store rates a vague question near zero risk, the draft now stands instead of getting a caveat.

## 0.1.3 - 2026-11-25

Eval and documentation release. No changes to the package API, prompts, or store schema.

### Eval

- `eval/org_store/`: a repeatable private-store eval. Fictional internal post-mortems are layered on the seed store, and each arm is checked for the private fact. `--org-store`, `--questions`, `--no-seed`, and `--retrieval-only` (no API key) run it on a team's own records.
- The benchmark judge grades caveats on biased items (specific filter, concrete evidence, settling data, no invented sources) and the report gives `rubric_by_arm`. "Never published" and similar phrases count as missing-data language.

### Docs

- README leads with the measured findings.
- `eval/org_store/README.md`: a guide for trialling the store on your team's post-mortems, including what a live run sends to the provider.

### Findings

On grok-4-fast-non-reasoning, the org-store eval gave the private fact in 8 of 8 shield answers and 0 of 8 without the store. On the graded rubric (same model as judge), the generic reminder scored 0.58 and the critic 0.78: the reminder never gave evidence about missing cases.

## 0.1.2 - 2026-11-25

Fixes found by live runs on a real model. No API or store schema changes.

### Changed

- Revisions state concrete facts from cited, confident store entries (counts, rates, identifiers) and change a conclusion the evidence contradicts instead of appending a caveat. Author priors still only name a selection filter.
- Final answers no longer mention the draft, critique, store, or retrieval.
- Plain factual answers no longer get a "no adjustment needed" note.
- Retrieval drops off-topic entries: a standard stop list, plural matching, the question itself must touch an entry, and a minimum score. Off-topic questions now retrieve nothing instead of filling k with unrelated entries.
- The CLI prints a short error instead of a traceback for an unrecorded fixture question, a missing API key, a failed provider call, or an invalid critic reply. `--debug` shows the full traceback.

### Eval

- Control answers fail when an arm adds an unneeded survivorship caveat; eval and benchmark report a per-arm control false-alarm rate. The rubric judge has an `unneeded_caveat` field.
- Answers that mention the pipeline fail scoring (`pipeline_leak`).
- `eval/benchmark/score.py` loads the repo `.env`.

### Findings

On grok-4-fast-non-reasoning the critic arms beat a generic survivorship reminder because the reminder adds caveats to factual questions. The store adds little on public knowledge the model already has, but with private records it supplied the exact facts (16/16 in a fictional internal post-mortem test, versus 0/16 without it).

## 0.1.1 - 2026-11-25

Fixes and eval additions. No API or store schema changes.

### Fixed

- `retrieve_k=0` now turns retrieval off for every question; before, some questions still reached the store, so the critic-only eval arm was not store-free.
- Factoid control questions are detected by their shape (short "what is", "how many", "which" questions without "because" or "given") instead of a list of topic phrases.
- A critic reply that is not valid `Critique` JSON raises `CritiqueParseError` (a `ValueError`), which keeps the raw reply for diagnosis.

### Added

- Eval: a `generic` arm that revises against one fixed survivorship-bias caution with no critic call, so the four arms (baseline, generic, critic-only, shield) separate "critic vs reminder" from "store vs no store". The README explains the arms. Fixture output marks arm differences as not meaningful.
- Eval error rows keep the critic's raw reply (`raw_critique`).
- The benchmark runner shares one draft across arms.
- `eval/export_gold.py --overlay`, and an xAI example in the README and `.env.example`.
- Store: every cited entry now links its source (19 of 26; the other 7 are author priors).

## 0.1.0 - 2026-11-24

First public alpha. The API, store schema, and prompts may still change.

### What it does

- Wald loop: the primary model drafts an answer without seeing the store, a separate critic reads retrieved Non-Survivor Store entries and returns structured `Critique` JSON, and the primary model revises the draft. CLI: `absencecritic "question"`. Library: `from absencecritic import run, score`.
- `score()` and `absencecritic --judge` critique an existing draft without generating or revising.
- Providers: recorded fixtures (default, no API key), any OpenAI-compatible endpoint (OpenAI, OpenRouter, local servers) with retries and backoff, and an optional local critic endpoint (`--critic local`).
- Non-Survivor Store: 26 seed entries with provenance. Entries backed only by the curator are tagged `evidence: author_prior`, capped at confidence 0.5, and flagged to the critic as weaker evidence.
- Store tooling: curated and catalog ingest (`absencecritic ingest`), a pending feedback queue that does not retrieve until accepted (`absencecritic feedback`), and a separate org store directory via `ABSENCECRITIC_STORE`.
- The wheel bundles the seed store and demo fixtures, so `pip install absencecritic` runs without a checkout.

### Evaluation tooling (repo checkout only)

- `eval/run_eval.py`: baseline, critic-only, and full-shield arms on one shared draft, with repeated samples and per-case error capture.
- `eval/benchmark/`: 26 held-out items (18 biased, 8 control) across 23 domains, a runner, a regex scorer, and a rubric judge that never calls the critic under test.
- Gold critique export with committed train and held-out splits, a human overlay, and a quarantine for live critic dumps.
- Out-of-CI recipes for critic fine-tuning and primary-model preference training.

### Known limitations

- Fixture eval 15/15 is a regression check against recorded answers, not a measured result.
- Benchmark labels are not yet independent: they were written by the project author or drafted by a coding agent (see issue #40). Treat benchmark numbers as provisional.
- Retrieval is keyword overlap, not embeddings.
- No live-model result is published with this release.

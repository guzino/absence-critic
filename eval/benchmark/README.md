<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Survivorship benchmark

Held-out questions with frozen labels. This is not fixture eval 15/15 and not critic JSON.

Labels (human/frozen):

- `should_caveate`
- `should_not_abstain`
- `must_mention_missing_data`

Large live judged JSONL files are not stored in git; see [artifacts/README.md](artifacts/README.md).

Run the arms, then score. Each item gets one draft that every arm reuses (baseline, generic caution, critic with no store, full shield; see the arm table in the main README), the same as `eval/run_eval.py`; answer rows carry `draft` and `retrieved_ids` so this can be checked. The regex scorer still matches words like "unknown"; the rubric judge (labelled `benchmark-rubric-heuristic` or `benchmark-rubric-llm`) does not call the critic under test. The report includes agreement between them.

```bash
python eval/benchmark/run.py --provider fixture --out eval/benchmark/answers.jsonl
python eval/benchmark/score.py --answers eval/benchmark/answers.jsonl
```

Each answer row: `{"id": "water-formula", "answer": "H2O"}`. Optional `arm` and `abstained` bool. `--judge none` skips the rubric. `--judge openai` is a separate live call, not `critic.critique`.

## Graded rubric

Pass/fail saturates: any caveat about missing data passes, so a one-line generic reminder scores like the full shield. On items labelled `should_caveate`, the judge also grades the caveat, one point each:

| Point | Meaning |
|-------|---------|
| `specific_filter` | Names this question's selection filter, not only "survivorship bias". |
| `concrete_evidence` | Gives a base rate, count, or named evidence about the missing cases. |
| `settling_data` | Says what data or comparison would settle the question. |
| `no_invented_sources` | Cites nothing fabricated. LLM judge only; the heuristic leaves it `null`. |

To judge with a different model family from the one that wrote the answers, set `ABSENCECRITIC_JUDGE_BASE_URL`, `ABSENCECRITIC_JUDGE_API_KEY`, and `ABSENCECRITIC_JUDGE_MODEL` (for example OpenRouter). Unset, the judge uses the answering provider. A judge URL without its own key is refused. The report names the judge in `judge_model`. `run.py --samples N` repeats each item and `score.py` then reports `sample_spread` per arm; `run.py --difficulty hard` runs only the hard items.

`rubric_score` is the fraction of scored points, and `rubric_by_arm` in the report gives the mean and per-point rates for each arm. The heuristic grades caveat paragraphs with keyword rules (query-word overlap, numbers, comparison words), so treat it as a floor and a CI check. Compare arms with `--judge openai`, and prefer a judge model different from the one that wrote the answers.

## Coverage and independence

`python eval/benchmark/score.py` with no `--answers` prints the current stats. As of this change: 38 items (26 biased, 12 control) across 34 domains, most of them not represented in the Non-Survivor Store.

12 items are marked `difficulty: hard`. Hard biased items do not name the filter in the question (cats that survived the fall reach the vet; the helmet law turns deaths into admissions). Hard controls are advice- or how-to-shaped questions that still need no survivorship caveat (a knot, basil, a comma rule). The report's `by_difficulty` gives judge pass rates, control false alarms, and rubric means for each level, since the standard items saturate.

Every item records an `annotator`. Labels from `guzino` (the author of the prompts and store) and `agent-draft` (drafted by a coding agent) are not independent; `independent_label_items` counts the rest and is 0 today. To raise it, a reviewer who did not write the prompts or store checks an item's labels and replaces `annotator` with their handle in a PR.

Only 5 items have recorded fixtures (`fixtures.yaml`). `run.py --provider fixture` runs those and lists the rest under `skipped_unrecorded`; the full set needs `--provider openai`. Fixture answers are hand-recorded, so a fixture score is a smoke test, not a result.

Benchmark ids and query text must not appear in `src/`, `tests/`, `eval/queries*.yaml`, eval fixtures, or gold. `tests/test_benchmark.py` enforces this.

Do not treat `score()` critique `survivorship_risk` as the gold label for this set. Do not train on these ids.

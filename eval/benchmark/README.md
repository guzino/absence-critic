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

Run the arms, then score. Each item gets one draft that every arm reuses (baseline, generic caution, critic with no store, full shield; see the arm table in the main README), the same as `eval/run_eval.py`; answer rows carry `draft` and `retrieved_ids` so this can be checked. The regex scorer still matches words like "unknown"; the rubric judge (labelled `benchmark-rubric-heuristic` or `benchmark-rubric-llm`) does not call the critic under test. The report includes agreement between them.

```bash
python eval/benchmark/run.py --provider fixture --out eval/benchmark/answers.jsonl
python eval/benchmark/score.py --answers eval/benchmark/answers.jsonl
```

Each answer row: `{"id": "water-formula", "answer": "H2O"}`. Optional `arm` and `abstained` bool. `--judge none` skips the rubric. `--judge openai` is a separate live call, not `critic.critique`.

## Coverage and independence

`python eval/benchmark/score.py` with no `--answers` prints the current stats. As of this change: 26 items (18 biased, 8 control) across 23 domains, most of them not represented in the Non-Survivor Store.

Every item records an `annotator`. Labels from `guzino` (the author of the prompts and store) and `agent-draft` (drafted by a coding agent) are not independent; `independent_label_items` counts the rest and is 0 today. To raise it, a reviewer who did not write the prompts or store checks an item's labels and replaces `annotator` with their handle in a PR.

Only 5 items have recorded fixtures (`fixtures.yaml`). `run.py --provider fixture` runs those and lists the rest under `skipped_unrecorded`; the full set needs `--provider openai`. Fixture answers are hand-recorded, so a fixture score is a smoke test, not a result.

Benchmark ids and query text must not appear in `src/`, `tests/`, `eval/queries*.yaml`, eval fixtures, or gold. `tests/test_benchmark.py` enforces this.

Do not treat `score()` critique `survivorship_risk` as the gold label for this set. Do not train on these ids.

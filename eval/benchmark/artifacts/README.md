<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Benchmark run artifacts

Committed here:

| File | Contents |
|------|----------|
| `grok-4-fast.score.json` | Aggregate independent-judge report for `grok-4-fast-non-reasoning` answers ([#106](https://github.com/guzino/absence-critic/issues/106)). No per-answer cases. |
| `openai-gpt-4o-mini.answers.jsonl` | 456 arm answers (38 items × 4 arms × 3 samples) from `openai/gpt-4o-mini` ([#109](https://github.com/guzino/absence-critic/issues/109)). |
| `openai-gpt-4o-mini.score.json` | Aggregate independent-judge report for those answers (same `gpt-4.1-mini` judge). Includes `sample_spread`, `rubric_by_arm` dimensions (including settling_data), and `by_difficulty`. No per-answer cases. |

Do not commit `.env` or files that embed API keys. Per-answer `cases` arrays are omitted from `*.score.json` to keep history small; rebuild them with:

```bash
python eval/benchmark/run.py --provider openai --samples 3 --out eval/benchmark/artifacts/my-run.answers.jsonl
python eval/benchmark/score.py --judge openai --answers eval/benchmark/artifacts/my-run.answers.jsonl
```

Set `ABSENCECRITIC_JUDGE_*` so the judge can differ from the answering model (see `.env.example`). The 4o-mini published score used an OpenAI-family judge; a cross-family judge on an open-weight answering model is still open on [#109](https://github.com/guzino/absence-critic/issues/109).
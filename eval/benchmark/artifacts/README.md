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
| `llama-3.3-70b.answers.jsonl` | 456 answers from open-weight `meta-llama/llama-3.3-70b-instruct` (OpenRouter); 6 arms recorded `CritiqueParseError`. |
| `llama-3.3-70b.score.json` | Aggregate report judged by **`grok-4-fast-non-reasoning` (xAI)** - different model family from the answering model ([#109](https://github.com/guzino/absence-critic/issues/109)). |
| `claude-sonnet-4.6.answers.jsonl` | 456 answers from `anthropic/claude-sonnet-4.6` (OpenRouter); 0 arm errors after retries. |
| `claude-sonnet-4.6.score.json` | Aggregate report judged by **`grok-4-fast-non-reasoning` (xAI)** - cross-family ([#109](https://github.com/guzino/absence-critic/issues/109) follow-on). Org-store not re-run for this model. |

Do not commit `.env` or files that embed API keys. Per-answer `cases` arrays are omitted from `*.score.json` to keep history small; rebuild them with:

```bash
python eval/benchmark/run.py --provider openai --samples 3 --out eval/benchmark/artifacts/my-run.answers.jsonl
python eval/benchmark/score.py --judge openai --answers eval/benchmark/artifacts/my-run.answers.jsonl
```

Set `ABSENCECRITIC_JUDGE_*` so the judge can differ from the answering model (see `.env.example`). The Llama 3.3 and Claude Sonnet 4.6 runs use a Grok judge (cross-family). The 4o-mini published score used an OpenAI-family judge.
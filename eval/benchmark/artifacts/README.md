<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Benchmark run artifacts

Independent-judge live runs (answers plus scored JSON) are **not** committed to this repository. They may contain model output you do not want in git history, and they go stale when prompts or items change.

To reproduce and archive a run:

```bash
python eval/benchmark/run.py --provider openai --samples 3 --out /path/to/bench.jsonl
python eval/benchmark/score.py --judge openai --answers /path/to/bench.jsonl
```

Set `ABSENCECRITIC_JUDGE_BASE_URL`, `ABSENCECRITIC_JUDGE_API_KEY`, and `ABSENCECRITIC_JUDGE_MODEL` in `.env` so the judge can differ from the answering model (see `.env.example`).

Publish summaries (pass rates, rubric means, false alarms) in issues or release notes; keep raw JSONL locally or attach them to a GitHub release if you need a fixed snapshot.
<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# AbsenceCritic

AbsenceCritic is a survivorship-bias shield for language models: a dedicated critic (the Wald Module) that reasons about the evidence that never made it into the training corpus, the retrieval index, or the evaluation set.

**AbsenceCritic was designed and originated by [Guzino](https://github.com/guzino).** The name, the architecture (Wald Module, Non-Survivor Store, Wald checklist), and the design documents in this repository are original work of that author. The historical inspiration is Abraham Wald’s 1943 aircraft-vulnerability analysis; the application of that method as an explicit second-brain critic for contemporary LLMs originated here.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).

Every source file carries the minimum clean mark:

```
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
```

## Conceptual origin

The original design package is kept in [`docs/`](docs/00-README.md) so the conceptual origin stays in the repository:

| Document | Title |
|----------|--------|
| [docs/00-README.md](docs/00-README.md) | Design package index |
| [docs/01-wald-origin.md](docs/01-wald-origin.md) | From Wald’s Notebook: The Armor That Is Not There |
| [docs/02-missing-planes-in-llms.md](docs/02-missing-planes-in-llms.md) | The Missing Planes in the Training Corpus |
| [docs/03-bulletproof-shield-design.md](docs/03-bulletproof-shield-design.md) | Bulletproof Shield Design |
| [docs/04-implementation-roadmap.md](docs/04-implementation-roadmap.md) | Implementation Roadmap and Engineering Notes |

Core claim: a model trained only on the planes that returned will correctly learn the distribution of survivable damage. Robustness requires an explicit process that reasons about the planes that did not return. That process is AbsenceCritic.

## Phase 0 — minimal shield

Python package plus CLI on a ports-and-adapters layout (`domain` / `application` / `adapters` / `prompts`). Loop: primary draft (no store) → keyword retrieval from the Non-Survivor Store → Wald critic JSON → primary revision. Tests and eval use recorded fixtures so they run without an API key.

Agent conventions (tool-agnostic): [`AGENTS.md`](AGENTS.md). Claude Code: [`CLAUDE.md`](CLAUDE.md). Humans: [`CONTRIBUTING.md`](CONTRIBUTING.md). Working plans for every roadmap phase (Wald pass, slices, measurable done): [`plans/`](plans/README.md). Work lands through pull requests, not direct pushes to `main`. Cursor loaders stay under [`.cursor/`](.cursor/); skill *content* is generic and is not duplicated per vendor.

### Install

```bash
python -m pip install absencecritic
```

The package bundles the seed Non-Survivor Store and the demo fixtures, so the CLI runs right after install with `--provider fixture`. Point `ABSENCECRITIC_STORE` at a writable directory before using `ingest` or `feedback`, so new entries do not land inside the installed package.

0.1.x is an alpha. See [`CHANGELOG.md`](CHANGELOG.md) for what it does and its known limits.

For development, from a checkout:

```bash
python -m pip install -e ".[dev]"
```

### CLI

```bash
absencecritic "What works for launching a startup?"
absencecritic --no-shield "What works for launching a startup?"
absencecritic --show-critique --json "What works for launching a startup?"
```

Curated store ingest (Phase 1; does not change the Wald loop):

```bash
absencecritic ingest path/to/entries.yaml
absencecritic ingest --catalog tests/fixtures/catalog.yaml
```

Valid entries are appended to `ingested.yaml` under the store directory. Duplicate `id` values are rejected. `--catalog` requires each row to cite an http(s) `source_url`.

User notes stay pending until accepted (confidence capped at 0.4; they do not retrieve before that):

```bash
absencecritic feedback path/to/note.yaml
absencecritic feedback --accept startup-user-note
```

Org failure memory is a **separate directory** on a private volume (`--store` or `ABSENCECRITIC_STORE`), not an ACL and not files dropped into `data/non_survivors/private/`. YamlStore skips a nested folder named `private` and does not retrieve it. Point the env var at the org store, ingest or copy citable notes there, and keep user notes pending until `absencecritic feedback --accept`. Do not commit patient-level or employer logs. Pair export refuses feedback/private ids unless `--allow-private`. The generator still never reads the store.

`--provider` is `fixture` unless `OPENAI_API_KEY` is set (then the default is `openai`). Force either:

```bash
absencecritic --provider fixture "What is 2+2?"
absencecritic --provider openai "What works for launching a startup?"
absencecritic --provider fixture --critic local "What works for launching a startup?"
absencecritic --judge --draft-file draft.txt --json "What works for launching a startup?"
```

Live OpenAI-compatible calls (OpenAI, OpenRouter, xAI, or a local server):

```bash
# OpenAI (Windows PowerShell)
$env:OPENAI_API_KEY = "..."
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"   # optional
$env:ABSENCECRITIC_MODEL = "gpt-4o-mini"             # optional
absencecritic --provider openai "What works for launching a startup?"

# OpenRouter
$env:OPENAI_API_KEY = "..."
$env:OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
<<<<<<< HEAD
$env:ABSENCECRITIC_MODEL = "openai/gpt-4o-mini"      # choose an available model slug
absencecritic --provider openai "What works for launching a startup?"

# Local OpenAI-compatible server (adjust URL/model for your server)
$env:OPENAI_API_KEY = "local"
$env:OPENAI_BASE_URL = "http://127.0.0.1:8080/v1"
$env:ABSENCECRITIC_MODEL = "local-model"
=======
$env:ABSENCECRITIC_MODEL = "openai/gpt-4o-mini"
absencecritic --provider openai "What works for launching a startup?"

# xAI (model names change; see https://docs.x.ai for current ones)
$env:OPENAI_API_KEY = "..."                          # your xAI API key
$env:OPENAI_BASE_URL = "https://api.x.ai/v1"
$env:ABSENCECRITIC_MODEL = "your-grok-model"
absencecritic --provider openai "What works for launching a startup?"

# Local OpenAI-compatible server (llama.cpp, vLLM, ...)
$env:OPENAI_API_KEY = "local"
$env:OPENAI_BASE_URL = "http://127.0.0.1:8080/v1"
$env:ABSENCECRITIC_MODEL = "your-local-model"
>>>>>>> origin/main
absencecritic --provider openai "What works for launching a startup?"
```

Copy [`.env.example`](.env.example) for the variable names. Store path: `ABSENCECRITIC_STORE` (default [`data/non_survivors/`](data/non_survivors/)).

Library:

```python
from absencecritic import run, score
from absencecritic.adapters.llm.fixture import FixtureLLM
from absencecritic.adapters.llm.openai_compat import OpenAICompat
from absencecritic.adapters.store.yaml_store import YamlStore
from absencecritic.paths import default_fixture_path, default_store_dir

result = run(
    "What works for launching a startup?",
    provider=FixtureLLM(default_fixture_path()),  # or OpenAICompat() after setting provider env vars
    store=YamlStore(default_store_dir()),
    shield=True,
)
print(result.final)
print(result.critique)

judged = score(
    "What works for launching a startup?",
    "Copy the last unicorn.",
    critic=FixtureLLM(default_fixture_path()),
    store=YamlStore(default_store_dir()),
)
print(judged.critique)
```

### Eval and tests

```bash
python eval/run_eval.py --provider fixture
python eval/benchmark/run.py --provider fixture --out eval/benchmark/answers.jsonl
python eval/benchmark/score.py --answers eval/benchmark/answers.jsonl
python -m pytest
```

<<<<<<< HEAD
[`eval/queries.yaml`](eval/queries.yaml) has ~12 survivor-biased questions and 3 controls. [`eval/fixtures/responses.yaml`](eval/fixtures/responses.yaml) holds recorded draft/critique/revision triples. Phase 2 gold critic JSONL is [`eval/gold/critiques.jsonl`](eval/gold/critiques.jsonl), split by committed ids in [`eval/gold/splits.yaml`](eval/gold/splits.yaml) into `train.jsonl` and `heldout.jsonl` (`python eval/export_gold.py` after fixture edits). Optional human edits go in [`eval/gold/overlay.yaml`](eval/gold/overlay.yaml) and win on the train/held-out export only; they do not rewrite fixtures. Live critic dumps go to gitignored `eval/gold/incoming/` via `python eval/log_incoming.py --query "..." --provider openai` and stay out of train until a human PR. Fixture 15/15 is product regression, not a training score. To refresh fixtures from a live model, run each query through the CLI with `--provider openai --json` and copy its output into the matching entry in that file. `python eval/export_gold.py --check` verifies committed gold exports without writing; `python eval/export_gold.py --out path/to/critiques.jsonl` writes exports to a chosen directory.
=======
Both eval runners generate one draft per question and run four arms on that same draft, so differences come from the arm and not from a different draft:

| Arm | Critic call | Store | What it isolates |
|-----|-------------|-------|------------------|
| `baseline` | no | no | The unrevised draft. |
| `generic` | no | no | A plain "watch for survivorship bias" revision: the reviser gets one fixed caution for every question ([`eval/eval_arms.py`](eval/eval_arms.py)). The cheapest alternative to AbsenceCritic. |
| `critic_only` | yes | no | The Wald critic with `retrieve_k=0`, so the loop never calls the store. Shows what the critic adds beyond the generic caution. |
| `shield` | yes | yes | The full loop. The gap to `critic_only` is what the Non-Survivor Store adds. |

The two middle arms are separate on purpose: `generic` answers "is a Wald critic better than a reminder?", and `critic_only` answers "does the store change the critique?". Neither question can be answered from fixtures. `FixtureLLM.revise` returns one recorded revision whatever critique it receives, so `generic`, `critic_only`, and `shield` all score 15/15 there, and fixture output says `arm_deltas_meaningful: false`. Only a live run (`--provider openai --samples 3`) shows whether the critic or the store actually changes answers.

[`eval/queries.yaml`](eval/queries.yaml) has ~12 survivor-biased questions and 3 controls. [`eval/fixtures/responses.yaml`](eval/fixtures/responses.yaml) holds recorded draft/critique/revision triples. Phase 2 gold critic JSONL is [`eval/gold/critiques.jsonl`](eval/gold/critiques.jsonl), split by committed ids in [`eval/gold/splits.yaml`](eval/gold/splits.yaml) into `train.jsonl` and `heldout.jsonl` (`python eval/export_gold.py` after fixture edits). Optional human edits go in [`eval/gold/overlay.yaml`](eval/gold/overlay.yaml) and win on the train/held-out export only; they do not rewrite fixtures. Live critic dumps go to gitignored `eval/gold/incoming/` via `python eval/log_incoming.py --query "..." --provider openai` and stay out of train until a human PR. Fixture 15/15 is product regression, not a training score. To refresh fixtures from a live model: `python eval/record_fixtures.py --provider openai --out eval/fixtures/responses.yaml`. Then `python eval/export_gold.py` (or `--check` without writing).
>>>>>>> origin/main

Critic fine-tune stays off CI: [`scripts/critic_train.md`](scripts/critic_train.md) (`python scripts/train_critic.py --dry-run`). Serve the result through `--critic local`. Do not train the generator on critique JSON. Primary-model DPO on pair export is [`scripts/primary_preference.md`](scripts/primary_preference.md) (`python scripts/train_primary.py --pairs ... --dry-run`). The default generator stays `--provider`; if controls start abstaining, the experiment failed.

Held-out survivorship items (disjoint ids, frozen labels, not critic JSON): [`eval/benchmark/`](eval/benchmark/README.md). Preference pairs (shielded vs unshielded, store bodies stripped): `python eval/export_pairs.py --provider fixture --out eval/pairs/out.jsonl`. Chosen is not a truth label.

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs pytest and fixture eval on `main` and pull requests. It never calls a live provider.

## Citation

If you use AbsenceCritic, please cite it as follows.

**Text**

[Guzino](https://github.com/guzino). *AbsenceCritic: A Survivorship-Bias Shield for Language Models*. Version 0.1.1, 2026. https://github.com/guzino/absence-critic

**BibTeX**

```bibtex
@software{guzino_absencecritic_2026,
  author  = {Guzino},
  title   = {AbsenceCritic: A Survivorship-Bias Shield for Language Models},
  year    = {2026},
  url     = {https://github.com/guzino/absence-critic},
  version = {0.1.1},
  license = {Apache-2.0},
  note    = {Original design and conceptual origin by Guzino (https://github.com/guzino)}
}
```

A machine-readable record is also provided in [`CITATION.cff`](CITATION.cff).

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

Private store files go in another directory (`--store` or `ABSENCECRITIC_STORE`) or `data/non_survivors/private/` (gitignored). Do not commit patient-level or employer failure logs. The generator still never reads the store.

`--provider` is `fixture` unless `OPENAI_API_KEY` is set (then the default is `openai`). Force either:

```bash
absencecritic --provider fixture "What is 2+2?"
absencecritic --provider openai "What works for launching a startup?"
```

Live OpenAI-compatible calls (OpenAI, OpenRouter, or a local server):

```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "..."
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"   # optional
$env:ABSENCECRITIC_MODEL = "gpt-4o-mini"             # optional
absencecritic --provider openai "What works for launching a startup?"
```

Copy [`.env.example`](.env.example) for the variable names. Store path: `ABSENCECRITIC_STORE` (default [`data/non_survivors/`](data/non_survivors/)).

Library:

```python
from absencecritic import run
from absencecritic.adapters.llm.fixture import FixtureLLM
from absencecritic.adapters.store.yaml_store import YamlStore
from absencecritic.paths import default_fixture_path, default_store_dir

result = run(
    "What works for launching a startup?",
    provider=FixtureLLM(default_fixture_path()),  # or OpenAICompat()
    store=YamlStore(default_store_dir()),
    shield=True,
)
print(result.final)
print(result.critique)
```

### Eval and tests

```bash
python eval/run_eval.py --provider fixture
python -m pytest
```

[`eval/queries.yaml`](eval/queries.yaml) has ~12 survivor-biased questions and 3 controls. [`eval/fixtures/responses.yaml`](eval/fixtures/responses.yaml) holds recorded draft/critique/revision triples. To refresh fixtures from a live model, run each query with `--provider openai --json` and replace the matching block in that file.

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs pytest and fixture eval on `main` and pull requests. It never calls a live provider.

## Citation

If you use AbsenceCritic, please cite it as follows.

**Text**

[Guzino](https://github.com/guzino). *AbsenceCritic: A Survivorship-Bias Shield for Language Models*. 2026. https://github.com/guzino

**BibTeX**

```bibtex
@software{guzino_absencecritic_2026,
  author  = {Guzino},
  title   = {AbsenceCritic: A Survivorship-Bias Shield for Language Models},
  year    = {2026},
  url     = {https://github.com/guzino},
  license = {Apache-2.0},
  note    = {Original design and conceptual origin by Guzino (https://github.com/guzino)}
}
```

A machine-readable record is also provided in [`CITATION.cff`](CITATION.cff).

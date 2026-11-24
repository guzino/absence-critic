<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Contributing

AbsenceCritic is Apache-2.0. Origin and architecture: [Guzino](https://github.com/guzino).

## Humans

1. Read [`docs/00-README.md`](docs/00-README.md) for the design, then [`AGENTS.md`](AGENTS.md) for the code layout and SOLID mapping. Execution order: [`plans/`](plans/README.md) (working plans; do not treat them as origin).
2. Keep the Wald invariant: the generator never reads the Non-Survivor Store.
3. Land work on a branch and open a pull request against `main`. Do not push features to `main`.
4. Run `python -m pytest` and `python eval/run_eval.py --provider fixture` before a PR. GitHub Actions runs the same pair (fixture provider only; no API keys) on `main` and every pull request. Pytest includes a UTF-8/control-character check so GitHub summaries cannot pick up BEL or replacement glyphs.
5. Live eval uses `OPENAI_API_KEY` (copy [`.env.example`](.env.example) to `.env`). Example: `python eval/run_eval.py --provider openai`.
6. SPDX header on new source files: `Copyright 2026 Guzino (https://github.com/guzino)` / `Apache-2.0`.
7. New Non-Survivor notes: `absencecritic ingest path/to/entries.yaml` (or a YAML file under `data/non_survivors/`). Provenance is required.
8. Fill the PR template. Reviewers should block on architecture/SOLID and the Wald invariant, not on taste.

## Pull requests

- One concern per PR (one layer or one user-visible change).
- New LLM or store backends implement ports; do not edit the loop unless the port changes.
- Reviews: architecture and SOLID first, then tests, then nits. Origin `docs/` stay frozen unless the PR is explicitly about them.

## Coding agents

Any tool: treat [`AGENTS.md`](AGENTS.md) as canonical. Do not fork rules per product.

- **Claude Code** loads [`CLAUDE.md`](CLAUDE.md), which points at AGENTS.md and the shared skills.
- **Cursor** loads `.cursor/rules/` and `.cursor/skills/` (skill *bodies* are generic; that directory is only the auto-load location).
- **GitHub Copilot** loads [`.github/copilot-instructions.md`](.github/copilot-instructions.md).

Skills live in one place (`.cursor/skills/*/SKILL.md`) so they cannot drift. Claude should `@` those paths rather than a duplicate `.claude/skills` tree. PR open/review skills are `open-pull-request` and `review-pull-request`.

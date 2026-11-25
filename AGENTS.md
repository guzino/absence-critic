<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# AbsenceCritic agent guide

Tool-agnostic rules for humans and coding agents (Claude Code, Cursor, Copilot, or anything else). Policy lives here. Editor-specific loaders are thin pointers; do not fork these rules per tool.

Ports-and-adapters around a linear Wald loop. Not LangGraph. Not a single mega-prompt.

**Invariant:** the generator never reads the Non-Survivor Store. Only the critic does.

## Layers

| Layer | Path | May import | Must not |
|-------|------|------------|----------|
| Domain | `src/absencecritic/domain/` | stdlib, pydantic | I/O, prompts, HTTP, adapters, application |
| Application | `src/absencecritic/application/` | domain, ports, stdlib | adapters, HTTP, YAML files |
| Prompts | `src/absencecritic/prompts/` | stdlib | pipeline logic, store I/O |
| Adapters | `src/absencecritic/adapters/` | domain, application.ports, prompts, I/O | other adapters' internals, collapsing stages |
| Eval | `eval/` | public facade / adapters | rewriting domain models |
| Origin docs | `docs/` | - | edits unless the user asked |
| Working plans | `plans/` | - | do not copy into origin `docs/` |

Public API: `from absencecritic import run, score, Critique, StoreEntry, PipelineResult`.

## Where a change goes

- New field on a critique or store entry -> `domain/`
- Loop steps (draft -> retrieve -> critique -> revise) -> `application/`
- Prompt wording -> `src/absencecritic/prompts/`
- HTTP, fixtures, YAML store, CLI -> `adapters/`
- New LLM backend -> `adapters/llm/` implementing `GeneratorPort` and `CriticPort`; do not edit `WaldLoop` unless the port itself changes
- New store backend -> `adapters/store/` implementing `StorePort`
- Eval queries/fixtures -> `eval/`
- Phase working plans (not origin) -> `plans/`

## Forbidden

- LangChain, LangGraph, DSPy in Phase 0-1
- Passing store hits into `generate`
- Inventing failure anecdotes not in the store or critique
- Store entries without `provenance`
- Business logic in the CLI
- Rewriting `docs/` origin documents unless asked
- Pushing feature work straight to `main` (use a pull request)

## SOLID (mapped to this repo)

Apply these on every change and every PR review. They are the same hexagonal rules as the layer table, not a second architecture.

| Principle | Here |
|-----------|------|
| **S**ingle responsibility | One layer, one Wald stage. Draft does not retrieve. CLI does not own loop policy. Prompts are text, not orchestration. |
| **O**pen/closed | New LLM or store = new adapter implementing a port. Do not edit `WaldLoop` unless the port contract itself changes. |
| **L**iskov | `FixtureLLM` and live adapters are substitutes on `GeneratorPort` / `CriticPort`. Critique still validates as `Critique` JSON. Generate still takes no store hits. |
| **I**nterface segregation | Keep `GeneratorPort`, `CriticPort`, and `StorePort` separate. Do not add store parameters to `generate` to "simplify". |
| **D**ependency inversion | Application depends on ports. Adapters depend inward. Domain never imports adapters. |

A PR that collapses draft+critic into one prompt, or that teaches `domain/` about HTTP, fails SOLID and architecture together.

## Pull requests

`main` is integration-only. Agents and humans land work through GitHub pull requests.

1. Branch from up-to-date `main` (`feat/...`, `fix/...`, `docs/...`). One concern per PR; split mixed layer dumps.
2. Do not commit `.env`, keys, or live eval transcripts that contain secrets.
3. Before opening: architecture-guard on the diff, `python -m pytest`, `python eval/run_eval.py --provider fixture`. Live eval only if the user asked.
4. PR body: why it exists and how to verify. Use `.github/pull_request_template.md`. Do not list files, "pointers," or invariants this diff did not touch. Write the body as a UTF-8 file and pass `--body-file`. Never embed markdown backticks in a PowerShell string: backtick+a is BEL and shows up as a replacement character in GitHub summaries. Plain text and emoji are fine; no curly quotes, ellipsis characters, or em dashes in commit/PR titles.
5. Reviewers (including agents): architecture and SOLID first, then tests, then nits. Block on invariant breaks. Do not rewrite origin `docs/` in a drive-by review.
6. Do not merge, force-push `main`, or skip hooks unless the user explicitly asked.
7. Address review comments with a new commit on the branch (or an explicit amend the user requested). Do not start a parallel rewrite on `main`.

Open-PR and review workflows: `.cursor/skills/open-pull-request/SKILL.md` and `.cursor/skills/review-pull-request/SKILL.md`.

## Workflows

Shared skill files (Agent Skills format; content is generic):

| Workflow | File |
|----------|------|
| Check layer imports and stage isolation | `.cursor/skills/architecture-guard/SKILL.md` |
| Add a Non-Survivor Store entry | `.cursor/skills/add-store-entry/SKILL.md` |
| Add an LLM adapter | `.cursor/skills/add-llm-adapter/SKILL.md` |
| Run pytest and fixture eval | `.cursor/skills/run-phase-eval/SKILL.md` |
| Open a GitHub pull request | `.cursor/skills/open-pull-request/SKILL.md` |
| Review a pull request | `.cursor/skills/review-pull-request/SKILL.md` |
| Update the public wiki in its published design | `.cursor/skills/update-wiki/SKILL.md` |

The `.cursor/skills/` path is where Cursor auto-loads skills. Claude Code should follow the same files via `CLAUDE.md`. Do not copy the bodies into a second tree.

## Tool adapters (pointers only)

- Claude Code: [`CLAUDE.md`](CLAUDE.md)
- GitHub Copilot: [`.github/copilot-instructions.md`](.github/copilot-instructions.md)
- Cursor: `.cursor/rules/`, `.cursor/skills/`, `.cursor/commands/`
- Humans: [`CONTRIBUTING.md`](CONTRIBUTING.md)

SPDX on every new source file:

```
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
```

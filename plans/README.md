<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Working plans

These files are **engineering working plans**. They are not origin documents. Conceptual spec stays in [`docs/`](../docs/00-README.md). Do not copy this folder into `docs/` and do not "improve" origin text while executing a slice.

Policy: [`AGENTS.md`](../AGENTS.md). One concern per GitHub PR. CI stays fixture-only and never sees live keys or GPUs.

## How each plan is written

Every phase plan is a Wald pass on the remaining work, not a task dump.

| Section | Job |
|---------|-----|
| Wald pass | Visible (already on `main` or in a prior phase), empty regions, unknown lethality, armor (what we refuse to ship as fake coverage). |
| Target shape | SOLID / layer table. New vendor = adapter. `WaldLoop` moves only when a port contract changes. |
| Slices | Small PRs with tests. "Not" lists so a slice cannot grow into the next phase. |
| Done | Measurable. Not "we added files." |
| Critic armor on the plan | How this plan itself can look rigorous while leaving the hole. |

Document 03 integration modes map onto phases; they are not extra products:

| Mode | Where it lives |
|------|----------------|
| Always-on / on-demand critic | Phase 0 (`shield=True` / `--no-shield`). |
| Evaluation harness (score a draft, no revise) | Phase 3 slice A. Fixture eval today still runs the full loop. |
| Training signal | Phase 3 slices B-C. Phase 2 may *produce* gold critiques; it does not fine-tune the primary model. |

## Index

| Phase | Origin name | Working plan | Status |
|-------|-------------|--------------|--------|
| 0 | Minimal Viable Shield | [`phase-0.md`](phase-0.md) | Shipped. Leftover holes listed so we do not reopen them as "Phase 0 bugs." |
| 1 | Persistent Failure Memory | [`phase-1.md`](phase-1.md) | Slices A-F on `main`. Honest subset of Document 04 (no crawler, no ACL server). |
| 2 | Specialized Critic Model | [`phase-2.md`](phase-2.md) | Slices A-F on `main`. Slice G (default specialized critic) is gated on held-out numbers. Prompted critic stays default. |
| 3 | Deeper Integration | [`phase-3.md`](phase-3.md) | Tracks A-F engineering on `main`. Document 04 success criteria are not claimed on fixture 15/15. |
| Next | Generative design | [`generative.md`](generative.md) | Prototype code, frozen briefs, and a fixture smoke test are in the tree. No live finding yet. Spec in [`docs/05-generative-absencecritic.md`](../docs/05-generative-absencecritic.md). Same invariant: the writer never reads the store. |

## Cross-phase armor

- Generator never reads the Non-Survivor Store. That sentence does not expire in Phase 2, Phase 3, or generative design.
- Critic output is still validated `Critique` JSON after a small model or a judge mode lands.
- No LangChain / LangGraph / DSPy as the loop. A fine-tune job is data plus an adapter, not a new orchestrator.
- Origin `docs/` stay frozen unless a PR is explicitly about them.
- Do not train on the same 15 fixture rows you then cite as 15/15 success.
- Do not scrape the live web in CI. Do not put patient-level or employer logs in the public seed.

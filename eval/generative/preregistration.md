<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Generative design pre-registration

**Dated:** 2026-11-25  
**Status:** committed before any live generative answers exist.

This locks the go/no-go margins for the first live run. Do not edit the numbers after that run begins. Spec: [`docs/05-generative-absencecritic.md`](../../docs/05-generative-absencecritic.md) section 5.

## Arms

| Arm | Definition |
|-----|------------|
| `baseline` | `generate` only |
| `creative` | "Be creative / unconventional" system prompt. No critic. No store. |
| `critic_only` | Design critique and expand with retrieval disabled |
| `shield` | Full `run_generative` with store |

Three samples per brief. Shared draft per brief and sample across arms that use a draft.

## Margins (0-1 scales unless noted)

A go requires all of the following on the frozen split, with an independent cross-family judge, and with no contradiction from the blind human subset:

1. Invented-source and invented-dead-design rates for `critic_only` and `shield` are no higher than `baseline` (target near zero on `shield`).
2. Mean feasibility of `shield` is not more than **0.10** below `baseline`.
3. Novelty of `shield` is higher than `baseline` and at least as high as `creative`.
4. Usefulness of `shield` is at least as high as `creative`, and not more than **0.10** below `baseline`.
5. Rationale quality is higher for `shield` than for `creative`, and `shield` beats `critic_only` on correct use of stored expired blockers when such entries are relevant.

## Humans

At least one rater must not have written the briefs or the store. Raters see the brief and the designs without arm names. If humans and the judge disagree on novelty or feasibility, trust the humans for the go/no-go and say so.

## No-go

Any failed margin above, human preference for `creative` on usefulness, or a spot-check that cites a dead design that was not retrieved.

<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Generative design eval

Offline harness for the gap-directed design loop. This is not a measured finding. Live runs happen only when someone asks.

## What this is

`run_generative` drafts a conventional answer, critiques the design space, expands into named gaps, then scores candidates. The writer never reads the store. See [`docs/05-generative-absencecritic.md`](../../docs/05-generative-absencecritic.md) and [`plans/generative.md`](../../plans/generative.md).

## Design-failure notes

Public seed: [`data/design_failures/entries.yaml`](../../data/design_failures/entries.yaml). It is not in the shield's default store (`data/non_survivors/`). `absencecritic design` reads this directory unless `--store` is set. The domain `discontinued_hardware` does not split into the words "design" or "product".

| Rule | Detail |
|------|--------|
| Provenance | Every entry needs a real citation or the exact author-prior phrase. |
| Author prior | Confidence at most 0.5. May name a convention. Must not invent a product, patent number, or kill date. |
| `blocker_status` | `active`, `expired`, or `unknown`. Mark `expired` only when a source shows the original constraint no longer holds, or a curator records that judgment in provenance. When unsure, use `unknown`. |
| IP | A revival sketch is an experimental design idea. It is not legal clearance and not a freedom-to-operate opinion. |
| Private kill lists | Stay in a separate org store. Do not commit them here. |

## Offline path

```text
python eval/generative/run_fixture.py
absencecritic design --provider fixture "Design a city bicycle for daily commuting. Hard constraints: two wheels, human power or assist under 250 W, under 20 kg. Useful means a rider can carry a bag and lock the bike outdoors."
```

## Frozen live protocol

Briefs, known-designs lists, arms, and go/no-go margins live in this folder. Do not change the margins after the first live answers exist. Pre-registration: [`preregistration.md`](preregistration.md).

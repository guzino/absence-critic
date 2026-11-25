<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

# Trial AbsenceCritic on your team's post-mortems

The Non-Survivor Store pays off when it holds failures the model cannot know: your cancelled launches, rolled-back migrations, people who left. This directory is a small eval built that way with fictional Northwind data. The same runner takes your records instead, so you can measure whether the store adds your facts to answers before you adopt it.

Expect an afternoon for about ten records and ten questions.

## 1. Decide what can leave the building

In a live run the critic sends each retrieved entry to your LLM provider. Only put text in the store that you are allowed to send there, or point `OPENAI_BASE_URL` at a local server. The generator never sees the store, but the critic does.

Keep your store in its own directory outside this repository (for example on a private volume). Do not commit it. A folder named `private` nested inside a store is skipped by retrieval, so do not put your entries there.

## 2. Write one entry per post-mortem

Copy the shape of [`store/org.yaml`](store/org.yaml):

```yaml
- id: acme-q3-pricing-tests
  domain: pricing
  selection_process: Only pricing tests that shipped got a retro doc.
  survivor_pattern: The two pricing-page tests that lifted conversion.
  non_survivor_evidence: 9 of 12 pricing tests in 2025 were rolled back for churn; see RETRO-418.
  confidence: 0.8
  provenance: Acme pricing retros 2025 (internal wiki)
```

- `provenance` is required and should name the real source. An entry whose provenance starts with "Author prior" only names a selection filter; its facts are never stated as evidence.
- `confidence` 0.7 or higher marks recorded evidence. The reviser then states its counts, rates, and identifiers exactly. Below 0.7 the entry only shapes the caveat.
- `non_survivor_evidence` is the fact you want answers to carry. Keep numbers and ticket ids in it.
- Retrieval is keyword-based and must overlap the question. Use the words people actually ask with (project names, team names, "playbook", "migration") in `survivor_pattern` and `selection_process`.

One entry per failure pattern beats one long summary: retrieval returns up to five entries.

## 3. Write the questions

Make a `questions.yaml` like [`questions.yaml`](questions.yaml). Each question should invite the survivor mistake its entry corrects, in the words a colleague would use:

```yaml
questions:
  - id: pricing-tests
    entry: acme-q3-pricing-tests
    query: Both pricing tests we wrote up lifted conversion. Should we run the same test on every plan?
    fact: '\b(9|nine)\b[^.]{0,60}(rolled back|churn)'
```

`fact` is a case-insensitive regex for the private fact in the final answer. Keep it loose enough to accept paraphrase around the number.

## 4. Check retrieval first (no API key)

```bash
python eval/org_store/run.py --retrieval-only --org-store /path/to/your/store --questions /path/to/questions.yaml
```

Every question should list its entry in `retrieved_ids`. Add `--no-seed` to test your store alone. If a question misses, add its words to the entry, not the other way round: real users will ask the way they ask. The live loop also matches on the draft, so live retrieval can only find more.

## 5. Run it live

```bash
python eval/org_store/run.py --provider openai --samples 2 --org-store /path/to/your/store --questions /path/to/questions.yaml --jsonl trial.jsonl
```

Each question gets one draft, then three arms on it:

| Arm | What it shows |
|-----|---------------|
| `baseline` | The model's answer alone. |
| `critic_only` | The Wald critic without the store. It can warn about missing failures but cannot name yours. |
| `shield` | The full loop with your store. |

Read `fact_rate` per arm. The useful result is `shield` well above the other two; on the Northwind data with `grok-4-fast-non-reasoning` it was 8 of 8 against 0 of 8. Then read a few `shield` answers in `trial.jsonl`: the fact should be stated plainly and attributed to your source, with no talk about the pipeline. `trial.jsonl` contains your records, so keep it with them.

## 6. Use it

```bash
export ABSENCECRITIC_STORE=/path/to/your/store     # PowerShell: $env:ABSENCECRITIC_STORE = "..."
absencecritic "Should every team adopt the pricing test that worked?"
```

`absencecritic ingest notes.yaml` appends validated entries to `ingested.yaml` in that directory and rejects duplicate ids. Notes from users go through `absencecritic feedback` and stay pending (confidence capped at 0.4) until someone runs `absencecritic feedback --accept <id>`.

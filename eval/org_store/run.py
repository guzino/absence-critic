# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Org-store eval: does the store add private facts the critic cannot know?

The store is the seed store plus eval/org_store/store/ (fictional Northwind
post-mortems), layered the way a team would add its own records. Arms share
one draft per question: baseline (no critique), critic_only (retrieve_k=0),
shield (full loop).

Fixture mode is a regression check: retrieval must find each question's
entry, and the recorded shield revision must carry its fact. Fixture arms all
return the same recorded revision, so arm differences are not a result there.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from absencecritic.adapters.llm.fixture import FixtureLLM  # noqa: E402
from absencecritic.adapters.llm.openai_compat import OpenAICompat  # noqa: E402
from absencecritic.adapters.store.yaml_store import YamlStore  # noqa: E402
from absencecritic.application.loop import run  # noqa: E402
from absencecritic.envfile import load_repo_env  # noqa: E402

ORG_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = ORG_DIR / "questions.yaml"
ORG_STORE = ORG_DIR / "store"
FIXTURES_PATH = ORG_DIR / "fixtures.yaml"
SEED_STORE = ROOT / "data" / "non_survivors"
ARMS = ("baseline", "critic_only", "shield")
_FIXTURE_HEADER = """\
# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0
#
# Recorded shield runs for the org-store eval (fictional Northwind data).
# Regenerate with: python eval/org_store/run.py --provider openai --record eval/org_store/fixtures.yaml
"""


def load_questions(path: Path = QUESTIONS_PATH) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["questions"]


def build_store(workdir: Path) -> YamlStore:
    """Seed store plus org entries in one directory, as a team would layer them."""
    for source in (SEED_STORE, ORG_STORE):
        for path in sorted(source.glob("*.yaml")):
            shutil.copy(path, workdir / f"{source.name}-{path.name}")
    return YamlStore(workdir)


def score_arm(question: dict, result) -> dict:
    return {
        "final": result.final,
        "retrieved_ids": result.retrieved_ids,
        "right_entry": question["entry"] in result.retrieved_ids,
        "fact": bool(re.search(question["fact"], result.final or "", re.I)),
    }


def run_question(question: dict, *, provider, store: YamlStore) -> dict:
    query = question["query"]
    draft = provider.generate(query=query)
    results = {
        "baseline": run(query, provider=provider, store=store, shield=False, draft=draft),
        "critic_only": run(query, provider=provider, store=store, retrieve_k=0, draft=draft),
        "shield": run(query, provider=provider, store=store, draft=draft),
    }
    return {
        "id": question["id"],
        "entry": question["entry"],
        "draft": draft,
        "arms": {arm: score_arm(question, res) for arm, res in results.items()},
        "critique": results["shield"].critique.model_dump(mode="json"),
    }


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    out = {}
    for arm in ARMS:
        facts = sum(1 for row in rows if row["arms"][arm]["fact"])
        out[arm] = {"fact_rate": facts / n if n else None}
    out["shield"]["right_entry_rate"] = (
        sum(1 for row in rows if row["arms"]["shield"]["right_entry"]) / n if n else None
    )
    return out


def write_fixtures(path: Path, questions: list[dict], rows: list[dict]) -> None:
    by_id = {q["id"]: q for q in questions}
    recorded = []
    for row in rows:
        if row["id"] in {r["query_id"] for r in recorded}:
            continue
        recorded.append(
            {
                "query_id": row["id"],
                "query": by_id[row["id"]]["query"],
                "draft": row["draft"],
                "critique": row["critique"],
                "revision": row["arms"]["shield"]["final"],
            }
        )
    body = yaml.safe_dump(
        [{k: v for k, v in r.items() if k != "query_id"} for r in recorded],
        sort_keys=False,
        allow_unicode=True,
    )
    path.write_text(_FIXTURE_HEADER + "\n" + body, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", choices=("fixture", "openai"), default="fixture")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--jsonl", type=Path, help="Write every row as JSONL")
    parser.add_argument("--record", type=Path, help="Write shield runs as fixtures (live only)")
    args = parser.parse_args(argv)
    if args.samples < 1:
        parser.error("--samples must be >= 1")
    if args.record and args.provider == "fixture":
        parser.error("--record needs --provider openai")
    load_repo_env()
    provider = FixtureLLM(FIXTURES_PATH) if args.provider == "fixture" else OpenAICompat()
    questions = load_questions()
    rows: list[dict] = []
    with tempfile.TemporaryDirectory() as tmp:
        store = build_store(Path(tmp))
        for sample in range(args.samples):
            for question in questions:
                row = run_question(question, provider=provider, store=store)
                row["sample"] = sample
                rows.append(row)
    if args.jsonl:
        args.jsonl.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            encoding="utf-8",
        )
    if args.record:
        write_fixtures(args.record, questions, rows)
    fixture = args.provider == "fixture"
    misses = Counter(row["id"] for row in rows if not row["arms"]["shield"]["right_entry"])
    no_fact = Counter(row["id"] for row in rows if not row["arms"]["shield"]["fact"])
    payload = {
        "provider": args.provider,
        "questions": len(questions),
        "samples": args.samples,
        "arms": summarise(rows),
        "retrieval_misses": sorted(misses),
        "shield_missing_fact": sorted(no_fact),
        "arm_deltas_meaningful": not fixture,
    }
    if fixture:
        payload["note"] = (
            "Fixture arms return one recorded revision, so only retrieval and the "
            "recorded shield fact are checked. Run --provider openai to compare arms."
        )
    print(json.dumps(payload, indent=2))
    return 0 if not misses and not no_fact else 1


if __name__ == "__main__":
    raise SystemExit(main())

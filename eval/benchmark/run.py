# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Run baseline and shielded arms over eval/benchmark/items.yaml."""

from __future__ import annotations

import argparse
import json
import sys
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

if str(ROOT / "eval") not in sys.path:
    sys.path.insert(0, str(ROOT / "eval"))
from eval_arms import FIXTURE_NOTE, generic_arm  # noqa: E402

ITEMS_PATH = Path(__file__).resolve().parent / "items.yaml"
BENCH_FIXTURES = Path(__file__).resolve().parent / "fixtures.yaml"


def _load_items(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"]


def _provider(name: str):
    if name == "fixture":
        return FixtureLLM(BENCH_FIXTURES)
    return OpenAICompat()


def fixture_queries(path: Path = BENCH_FIXTURES) -> set[str]:
    rows = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return {str(row["query"]).strip() for row in rows}


def split_recorded(items: list[dict], recorded: set[str]) -> tuple[list[dict], list[str]]:
    """Fixture mode only runs recorded items; the rest need a live provider."""
    runnable = [item for item in items if item["query"].strip() in recorded]
    skipped = [item["id"] for item in items if item["query"].strip() not in recorded]
    return runnable, skipped


def write_answers(items: list[dict], *, provider, store, out) -> list[dict]:
    """One draft per item, reused by every arm (same arms as eval/run_eval.py)."""
    rows = []
    for item in items:
        query = item["query"]
        draft = provider.generate(query=query)
        arms = (
            ("baseline", run(query, provider=provider, store=store, shield=False, draft=draft)),
            ("generic", generic_arm(query, draft, generator=provider)),
            (
                "critic_only",
                run(query, provider=provider, store=store, retrieve_k=0, draft=draft),
            ),
            ("shield", run(query, provider=provider, store=store, draft=draft)),
        )
        for arm, result in arms:
            row = {
                "id": item["id"],
                "arm": arm,
                "draft": result.draft,
                "retrieved_ids": result.retrieved_ids,
                "answer": result.final,
            }
            rows.append(row)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run AbsenceCritic over the survivorship benchmark items."
    )
    parser.add_argument("--provider", choices=("fixture", "openai"), default="fixture")
    parser.add_argument("--items", type=Path, default=ITEMS_PATH)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Answers JSONL for eval/benchmark/score.py --answers",
    )
    args = parser.parse_args(argv)
    load_repo_env()
    items = _load_items(args.items)
    skipped: list[str] = []
    if args.provider == "fixture":
        items, skipped = split_recorded(items, fixture_queries())
    provider = _provider(args.provider)
    store = YamlStore(ROOT / "data" / "non_survivors")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        rows = write_answers(items, provider=provider, store=store, out=handle)
    summary = {"wrote": len(rows), "path": str(args.out), "skipped_unrecorded": skipped}
    if args.provider == "fixture":
        summary["note"] = FIXTURE_NOTE
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

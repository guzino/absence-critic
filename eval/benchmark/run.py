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
from absencecritic.adapters.llm.openai_compat import LLMError, OpenAICompat  # noqa: E402
from absencecritic.adapters.store.yaml_store import YamlStore  # noqa: E402
from absencecritic.application.loop import CritiqueParseError, run  # noqa: E402
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


def _arm_call(name: str, fn):
    """Run one arm; open-weight models may return invalid critic JSON."""
    try:
        return fn(), None
    except Exception as exc:  # noqa: BLE001 — record and continue the live matrix
        return None, f"{type(exc).__name__}: {exc}"


def write_answers(items: list[dict], *, provider, store, out, samples: int = 1) -> list[dict]:
    """One draft per item and sample, reused by every arm (same arms as eval/run_eval.py).

    Arm failures (bad critic JSON, HTTP errors) are written as rows with `error` set
    so a full 3-sample live run can finish on weaker models.
    """
    rows = []
    for sample, item in ((s, i) for s in range(samples) for i in items):
        query = item["query"]
        try:
            draft = provider.generate(query=query)
        except (LLMError, OSError, ValueError) as exc:
            for arm in ("baseline", "generic", "critic_only", "shield"):
                row = {
                    "id": item["id"],
                    "arm": arm,
                    "sample": sample,
                    "draft": "",
                    "retrieved_ids": [],
                    "answer": "",
                    "error": f"generate {type(exc).__name__}: {exc}",
                }
                rows.append(row)
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
            continue
        arm_fns = (
            ("baseline", lambda: run(query, provider=provider, store=store, shield=False, draft=draft)),
            ("generic", lambda: generic_arm(query, draft, generator=provider)),
            (
                "critic_only",
                lambda: run(query, provider=provider, store=store, retrieve_k=0, draft=draft),
            ),
            ("shield", lambda: run(query, provider=provider, store=store, draft=draft)),
        )
        for arm, fn in arm_fns:
            result, err = _arm_call(arm, fn)
            if err:
                row = {
                    "id": item["id"],
                    "arm": arm,
                    "sample": sample,
                    "draft": draft,
                    "retrieved_ids": [],
                    "answer": "",
                    "error": err,
                }
            else:
                row = {
                    "id": item["id"],
                    "arm": arm,
                    "sample": sample,
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
    parser.add_argument("--samples", type=int, default=1, help="Repeat each item (live variance)")
    parser.add_argument(
        "--difficulty", choices=("hard", "standard"), help="Only run items of this difficulty"
    )
    args = parser.parse_args(argv)
    if args.samples < 1:
        parser.error("--samples must be >= 1")
    load_repo_env()
    items = _load_items(args.items)
    if args.difficulty:
        items = [i for i in items if i.get("difficulty", "standard") == args.difficulty]
    skipped: list[str] = []
    if args.provider == "fixture":
        items, skipped = split_recorded(items, fixture_queries())
    provider = _provider(args.provider)
    store = YamlStore(ROOT / "data" / "non_survivors")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        rows = write_answers(
            items, provider=provider, store=store, out=handle, samples=args.samples
        )
    n_error = sum(1 for row in rows if row.get("error"))
    summary = {
        "wrote": len(rows),
        "path": str(args.out),
        "skipped_unrecorded": skipped,
        "arm_errors": n_error,
    }
    if args.provider == "fixture":
        summary["note"] = FIXTURE_NOTE
    print(json.dumps(summary, indent=2))
    return 1 if n_error else 0


if __name__ == "__main__":
    raise SystemExit(main())

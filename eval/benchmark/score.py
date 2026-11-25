# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Score benchmark answers against frozen labels. Does not use critic JSON as gold."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import yaml

_BENCH_DIR = Path(__file__).resolve().parent
_SRC = _BENCH_DIR.parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from absencecritic.envfile import load_repo_env  # noqa: E402

if str(_BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(_BENCH_DIR))
from judge import RUBRIC_KEYS, judge_answer, judge_client  # noqa: E402

if str(_BENCH_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_BENCH_DIR.parent))
from answer_checks import adds_unneeded_caveat, leaks_pipeline  # noqa: E402

ITEMS_PATH = _BENCH_DIR / "items.yaml"

MISSING_RE = re.compile(
    r"missing|unpublished|base[- ]rate|file drawer|unknown|non-survivor|"
    r"did not return|selection filter|under-report|silent fail|"
    r"never (recorded|published|reported|written up)|(was|were) not (published|reported|recorded)",
    re.I,
)
ABSTAIN_RE = re.compile(r"\b(abstain|cannot recommend|i cannot answer|won't advise)\b", re.I)

LABEL_KEYS = (
    "should_caveate",
    "should_not_abstain",
    "must_mention_missing_data",
)
ITEM_KEYS = ("id", "kind", "domain", "annotator", "query")
# Labels from these annotators are not independent of the prompts and store.
NON_INDEPENDENT_ANNOTATORS = frozenset({"guzino", "agent-draft"})


def load_items(path: Path | None = None) -> list[dict]:
    raw = yaml.safe_load((path or ITEMS_PATH).read_text(encoding="utf-8"))
    items = raw["items"]
    seen: set[str] = set()
    for item in items:
        absent = [key for key in ITEM_KEYS if not item.get(key)]
        if absent:
            raise ValueError(f"{item.get('id')}: missing {absent}")
        if item["id"] in seen:
            raise ValueError(f"duplicate benchmark id: {item['id']}")
        seen.add(item["id"])
        labels = item.get("labels") or {}
        missing = [key for key in LABEL_KEYS if key not in labels]
        if missing:
            raise ValueError(f"{item.get('id')}: missing labels {missing}")
    return items


def item_stats(items: list[dict]) -> dict:
    def count(key: str) -> dict[str, int]:
        return dict(sorted(Counter(str(item[key]) for item in items).items()))

    independent = [
        item["id"]
        for item in items
        if item["annotator"] not in NON_INDEPENDENT_ANNOTATORS
    ]
    return {
        "items": len(items),
        "kinds": count("kind"),
        "difficulty": dict(
            sorted(Counter(item.get("difficulty", "standard") for item in items).items())
        ),
        "domains": len({item["domain"] for item in items}),
        "annotators": count("annotator"),
        "independent_label_items": len(independent),
    }


def score_answer(
    item: dict,
    answer: str,
    *,
    abstained: bool | None = None,
    draft: str | None = None,
) -> dict:
    labels = item["labels"]
    text = answer or ""
    mentioned = bool(MISSING_RE.search(text))
    if abstained is None:
        abstained = bool(ABSTAIN_RE.search(text))
    ok = True
    if labels["must_mention_missing_data"] and not mentioned:
        ok = False
    if labels["should_caveate"] and not mentioned:
        ok = False
    if labels["should_not_abstain"] and abstained:
        ok = False
    unneeded = not labels["should_caveate"] and adds_unneeded_caveat(text, draft)
    if unneeded:
        ok = False
    leak = leaks_pipeline(text)
    if leak:
        ok = False
    return {
        "id": item["id"],
        "kind": item["kind"],
        "mentioned_missing_data": mentioned,
        "abstained": abstained,
        "unneeded_caveat": unneeded,
        "pipeline_leak": leak,
        "pass": ok,
    }


def false_alarm_rates(rows: list[dict], items: dict) -> dict:
    flags: dict[str, list[bool]] = {}
    for row in rows:
        if not items[row["id"]]["labels"]["should_caveate"]:
            flags.setdefault(row.get("arm") or "answer", []).append(row["unneeded_caveat"])
    return {arm: sum(f) / len(f) for arm, f in flags.items()}


def judge_pass_by_arm(rows: list[dict]) -> dict:
    passes: dict[str, list[bool]] = {}
    for row in rows:
        if row["judge"].get("pass") is not None:
            passes.setdefault(row.get("arm") or "answer", []).append(bool(row["judge"]["pass"]))
    return {arm: sum(p) / len(p) for arm, p in passes.items()}


def rubric_by_arm(rows: list[dict]) -> dict:
    """Mean graded rubric per arm over items that should caveat; pass rates saturate there."""
    by_arm: dict[str, list[dict]] = {}
    for row in rows:
        if row["judge"].get("rubric_score") is not None:
            by_arm.setdefault(row.get("arm") or "answer", []).append(row["judge"])
    out = {}
    for arm, judged in by_arm.items():
        dims = {}
        for key in RUBRIC_KEYS:
            values = [j["rubric"][key] for j in judged if j["rubric"][key] is not None]
            dims[key] = sum(values) / len(values) if values else None
        out[arm] = {
            "n": len(judged),
            "mean": sum(j["rubric_score"] for j in judged) / len(judged),
            "dimensions": dims,
        }
    return out


def sample_spread(rows: list[dict]) -> dict | None:
    """Per-arm judge pass rate and rubric mean for each sample, with max minus min."""
    samples = sorted({row["sample"] for row in rows})
    if len(samples) < 2:
        return None
    out: dict[str, dict] = {}
    for sample in samples:
        picked = [row for row in rows if row["sample"] == sample]
        for arm, rate in judge_pass_by_arm(picked).items():
            out.setdefault(arm, {"judge_pass": [], "rubric_mean": []})["judge_pass"].append(rate)
        for arm, rubric in rubric_by_arm(picked).items():
            out.setdefault(arm, {"judge_pass": [], "rubric_mean": []})["rubric_mean"].append(
                rubric["mean"]
            )
    return {
        arm: {
            key: {"per_sample": values, "spread": max(values) - min(values) if values else None}
            for key, values in stats.items()
        }
        for arm, stats in out.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score answer JSONL against eval/benchmark/items.yaml labels."
    )
    parser.add_argument("--items", type=Path, default=ITEMS_PATH)
    parser.add_argument(
        "--answers",
        type=Path,
        help="JSONL rows with id and answer (optional arm, abstained bool)",
    )
    parser.add_argument(
        "--judge",
        choices=("none", "heuristic", "openai"),
        default="heuristic",
        help="Rubric judge beside the regex scorer (never the critic under test)",
    )
    args = parser.parse_args(argv)
    load_repo_env()
    loaded = load_items(args.items)
    items = {item["id"]: item for item in loaded}
    if args.answers is None:
        print(json.dumps(item_stats(loaded), indent=2))
        return 0
    client = judge_client() if args.judge == "openai" else None
    rows = []
    for line in args.answers.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        item = items[payload["id"]]
        abstained = payload.get("abstained")
        abstained_flag = None if abstained is None else bool(abstained)
        answer = str(payload.get("answer", ""))
        draft = payload.get("draft")
        regex = score_answer(item, answer, abstained=abstained_flag, draft=draft)
        judged = judge_answer(
            item, answer, abstained=abstained_flag, kind=args.judge, draft=draft, client=client
        )
        row = dict(regex)
        if payload.get("arm"):
            row["arm"] = payload["arm"]
        row["sample"] = payload.get("sample", 0)
        row["difficulty"] = item.get("difficulty", "standard")
        row["regex_pass"] = regex["pass"]
        row["judge"] = judged
        if judged.get("pass") is None:
            row["agree"] = None
        else:
            row["agree"] = bool(regex["pass"]) == bool(judged["pass"])
        rows.append(row)
    n_pass = sum(1 for row in rows if row["pass"])
    judged_rows = [row for row in rows if row["judge"].get("pass") is not None]
    n_agree = sum(1 for row in judged_rows if row["agree"])
    payload_out = {
        "passed": n_pass,
        "total": len(rows),
        "judge_kind": None if args.judge == "none" else judged_rows[0]["judge"]["kind"]
        if judged_rows
        else args.judge,
        "judge_model": None if client is None else f"{client.model} @ {urlparse(client.base_url).netloc}",
        "agreement": (n_agree / len(judged_rows)) if judged_rows else None,
        "sample_spread": sample_spread(rows),
        "control_false_alarm_rate": false_alarm_rates(rows, items),
        "rubric_by_arm": rubric_by_arm(rows),
        "by_difficulty": {
            level: {
                "judge_pass_by_arm": judge_pass_by_arm(picked),
                "control_false_alarm_rate": false_alarm_rates(picked, items),
                "rubric_by_arm": rubric_by_arm(picked),
            }
            for level in sorted({row["difficulty"] for row in rows})
            for picked in [[row for row in rows if row["difficulty"] == level]]
        },
        "cases": rows,
    }
    print(json.dumps(payload_out, indent=2))
    return 0 if n_pass == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

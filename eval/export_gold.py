# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Freeze fixture critiques as (query, draft, gold critique) JSONL for Phase 2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from absencecritic.domain.models import Critique  # noqa: E402
from absencecritic.paths import default_fixture_path  # noqa: E402

GOLD_DIR = ROOT / "eval" / "gold"
GOLD_PATH = GOLD_DIR / "critiques.jsonl"
TRAIN_PATH = GOLD_DIR / "train.jsonl"
HELDOUT_PATH = GOLD_DIR / "heldout.jsonl"
SPLITS_PATH = GOLD_DIR / "splits.yaml"
OVERLAY_PATH = GOLD_DIR / "overlay.yaml"
QUERIES_PATH = ROOT / "eval" / "queries.yaml"
PROVENANCE = "eval/fixtures/responses.yaml"
OVERLAY_FIELDS = ("id", "editor", "date", "reason", "critique")


def _query_index() -> dict[str, dict[str, str]]:
    raw = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))
    index: dict[str, dict[str, str]] = {}
    for item in raw["queries"]:
        query = str(item["query"]).strip()
        index[query] = {"id": str(item["id"]), "kind": str(item["kind"])}
    return index


def load_splits(path: Path | None = None) -> tuple[list[str], list[str]]:
    raw = yaml.safe_load((path or SPLITS_PATH).read_text(encoding="utf-8"))
    train = [str(x) for x in raw["train"]]
    heldout = [str(x) for x in raw["heldout"]]
    overlap = set(train) & set(heldout)
    if overlap:
        raise ValueError(f"split ids in both train and heldout: {sorted(overlap)}")
    if not train or not heldout:
        raise ValueError("train and heldout lists must both be non-empty")
    return train, heldout


def load_overlays(path: Path | None = None) -> dict[str, dict]:
    overlay_path = path or OVERLAY_PATH
    if not overlay_path.is_file():
        return {}
    raw = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
    rows = raw.get("overlays", raw if isinstance(raw, list) else [])
    if not rows:
        return {}
    by_id: dict[str, dict] = {}
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("overlay row must be a mapping")
        missing = [name for name in OVERLAY_FIELDS if not item.get(name)]
        if missing:
            raise ValueError(f"overlay row missing {missing}")
        qid = str(item["id"])
        if qid in by_id:
            raise ValueError(f"duplicate overlay id: {qid}")
        critique = Critique.model_validate(item["critique"])
        by_id[qid] = {
            "id": qid,
            "editor": str(item["editor"]),
            "date": str(item["date"]),
            "reason": str(item["reason"]),
            "critique": critique.model_dump(mode="json"),
        }
    return by_id


def apply_overlay(records: list[dict], overlays: dict[str, dict]) -> list[dict]:
    gold_ids = {row["id"] for row in records}
    unknown = sorted(set(overlays) - gold_ids)
    if unknown:
        raise ValueError(f"overlay ids not in gold: {unknown}")
    applied: list[dict] = []
    for row in records:
        overlay = overlays.get(row["id"])
        if overlay is None:
            applied.append(row)
            continue
        updated = dict(row)
        updated["critique"] = overlay["critique"]
        updated["critique_source"] = "overlay"
        updated["overlay_editor"] = overlay["editor"]
        updated["overlay_date"] = overlay["date"]
        updated["overlay_reason"] = overlay["reason"]
        applied.append(updated)
    return applied


<<<<<<< HEAD
def _jsonl_text(rows: list[dict]) -> str:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    return "\n".join(lines) + "\n"


def _dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_jsonl_text(rows), encoding="utf-8")


=======
>>>>>>> origin/main
def gold_records(fixture_path: Path | None = None) -> list[dict]:
    path = fixture_path or default_fixture_path()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("responses", [])
    if not isinstance(raw, list):
        raise ValueError(f"Expected a list of fixture responses in {path}")
    index = _query_index()
    records: list[dict] = []
    for item in raw:
        query = str(item["query"]).strip()
        meta = index.get(query)
        if meta is None:
            raise ValueError(f"fixture query has no eval/queries.yaml id: {query!r}")
        critique = Critique.model_validate(item["critique"])
        records.append(
            {
                "id": meta["id"],
                "query": query,
                "kind": meta["kind"],
                "draft": str(item["draft"]),
                "critique": critique.model_dump(mode="json"),
                "provenance": PROVENANCE,
            }
        )
    records.sort(key=lambda row: row["id"])
    return records


def _partition(records: list[dict]) -> tuple[list[dict], list[dict]]:
    train_ids, heldout_ids = load_splits()
    train_set, heldout_set = set(train_ids), set(heldout_ids)
    gold_ids = {row["id"] for row in records}
    missing = (train_set | heldout_set) - gold_ids
    extra = gold_ids - train_set - heldout_set
    if missing:
        raise ValueError(f"splits.yaml ids not in gold: {sorted(missing)}")
    if extra:
        raise ValueError(f"gold ids missing from splits.yaml: {sorted(extra)}")
    heldout_kinds = {row["kind"] for row in records if row["id"] in heldout_set}
    if "biased" not in heldout_kinds or "control" not in heldout_kinds:
        raise ValueError("heldout must include at least one biased and one control id")
    train = [row for row in records if row["id"] in train_set]
    heldout = [row for row in records if row["id"] in heldout_set]
    return train, heldout


def rendered_gold(*, overlay_path: Path | None = None) -> dict[str, str]:
    records = gold_records()
    overlaid = apply_overlay(records, load_overlays(overlay_path))
    train, heldout = _partition(overlaid)
    return {
        "critiques.jsonl": _jsonl_text(records),
        "train.jsonl": _jsonl_text(train),
        "heldout.jsonl": _jsonl_text(heldout),
    }


def _jsonl_text(rows: list[dict]) -> str:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    return "\n".join(lines) + "\n"


def write_gold(
    dest: Path | None = None, *, overlay_path: Path | None = None
) -> Path:
    payloads = rendered_gold(overlay_path=overlay_path)
    out = dest or GOLD_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payloads["critiques.jsonl"], encoding="utf-8")
    out.parent.joinpath("train.jsonl").write_text(
        payloads["train.jsonl"], encoding="utf-8"
    )
    out.parent.joinpath("heldout.jsonl").write_text(
        payloads["heldout.jsonl"], encoding="utf-8"
    )
    return out


<<<<<<< HEAD
def check_gold(
    dest: Path | None = None, *, overlay_path: Path | None = None
) -> list[Path]:
    """Return generated gold files that are absent or differ from disk."""
    records = gold_records()
    overlaid = apply_overlay(records, load_overlays(overlay_path))
    train, heldout = _partition(overlaid)
    out = dest or GOLD_PATH
    expected = {
        out: _jsonl_text(records),
        out.parent / TRAIN_PATH.name: _jsonl_text(train),
        out.parent / HELDOUT_PATH.name: _jsonl_text(heldout),
    }
    return [
        path
        for path, content in expected.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != content
    ]
=======
def check_gold(*, overlay_path: Path | None = None) -> list[str]:
    payloads = rendered_gold(overlay_path=overlay_path)
    stale: list[str] = []
    mapping = {
        "critiques.jsonl": GOLD_PATH,
        "train.jsonl": TRAIN_PATH,
        "heldout.jsonl": HELDOUT_PATH,
    }
    for name, path in mapping.items():
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if current != payloads[name]:
            stale.append(name)
    return stale
>>>>>>> origin/main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
<<<<<<< HEAD
        description="Export or check committed gold eval files"
=======
        description="Freeze fixture critiques as gold JSONL. Overlay applies to train/held-out only."
>>>>>>> origin/main
    )
    parser.add_argument(
        "--out",
        type=Path,
<<<<<<< HEAD
        default=GOLD_PATH,
        help="output path for critiques JSONL; train and heldout are written beside it",
=======
        help="Write critiques.jsonl here; train.jsonl and heldout.jsonl are siblings",
>>>>>>> origin/main
    )
    parser.add_argument(
        "--check",
        action="store_true",
<<<<<<< HEAD
        help="exit non-zero if generated files differ; do not write",
    )
    args = parser.parse_args(argv)
    if args.check:
        stale = check_gold(args.out)
        if stale:
            print("Stale gold files:")
            for path in stale:
                print(path.as_posix())
            return 1
        print("Gold files are up to date.")
        return 0
    path = write_gold(args.out)
=======
        help="Exit 1 if committed gold files are stale; do not write",
    )
    parser.add_argument(
        "--overlay",
        type=Path,
        help=f"Overlay YAML to apply instead of {OVERLAY_PATH.relative_to(ROOT).as_posix()}",
    )
    args = parser.parse_args(argv)
    if args.overlay is not None and not args.overlay.is_file():
        parser.error(f"overlay not found: {args.overlay}")
    if args.check:
        stale = check_gold(overlay_path=args.overlay)
        if stale:
            print("stale: " + ", ".join(stale))
            return 1
        print("gold files match export")
        return 0
    path = write_gold(args.out, overlay_path=args.overlay)
>>>>>>> origin/main
    print(path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Compare baseline vs shielded answers using fixtures (no API key).

<<<<<<< HEAD
To refresh fixtures from a live model, follow the manual workflow in README.md:
run each query through the CLI with --provider openai --json and copy the
result into the matching entry in eval/fixtures/responses.yaml.
=======
Regenerate live fixtures later:
  python eval/record_fixtures.py --provider openai --out eval/fixtures/responses.yaml
>>>>>>> origin/main
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from absencecritic.adapters.llm.fixture import FixtureLLM  # noqa: E402
from absencecritic.adapters.llm.openai_compat import OpenAICompat  # noqa: E402
from absencecritic.adapters.store.yaml_store import YamlStore  # noqa: E402
from absencecritic.application.loop import run  # noqa: E402
from absencecritic.envfile import load_repo_env  # noqa: E402

EVAL_DIR = ROOT / "eval"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
from answer_checks import adds_unneeded_caveat, leaks_pipeline  # noqa: E402
from eval_arms import FIXTURE_NOTE, generic_arm  # noqa: E402

ARMS = ("baseline", "generic", "critic_only", "shield")

MISSING_RE = re.compile(
    r"surviv|missing|unpublished|base[- ]rate|file drawer|unknown|caveat|"
    r"did not return|non-survivor|selection|under-report|failure rate|"
    r"without data|cannot reveal|visible sample",
    re.I,
)
RAW_CRITIQUE_LIMIT = 4000
ABSTAIN_RE = re.compile(
    r"\b(abstain|cannot recommend|i cannot answer|won't advise)\b", re.I
)


def load_queries(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["queries"]


def _arm_pass(kind: str, text: str, critique, *, draft: str | None = None) -> bool:
    if leaks_pipeline(text):
        return False
    missing_lang = bool(MISSING_RE.search(text or ""))
    abstained_text = bool(ABSTAIN_RE.search(text or ""))
    adjustment = critique.confidence_adjustment.value if critique else None
    if kind == "control":
        if adds_unneeded_caveat(text, draft):
            return False
        if critique is not None:
            return adjustment != "abstain" and critique.survivorship_risk < 0.5
        return not abstained_text
    if critique is not None:
        return missing_lang and adjustment in {"lower", "seek_more_data", "abstain"}
    return missing_lang


def score_arm(item: dict, result) -> dict:
    critique = result.critique
    text = result.final
    used_store = False
    if critique and result.retrieved_ids:
        used = {h.id for h in critique.non_survivors}
        used_store = bool(used & set(result.retrieved_ids)) or bool(critique.non_survivors)
    adjustment = critique.confidence_adjustment.value if critique else None
    return {
        "draft": result.draft,
        "final": result.final,
        "retrieved_ids": result.retrieved_ids,
        "survivorship_risk": critique.survivorship_risk if critique else None,
        "confidence_adjustment": adjustment,
        "missing_data_language": bool(MISSING_RE.search(text or "")),
        "used_store_ids": used_store,
        "pipeline_leak": leaks_pipeline(text),
        "unneeded_caveat": item["kind"] == "control"
        and adds_unneeded_caveat(text, result.draft),
        "chars": len(result.final or ""),
        "pass": _arm_pass(item["kind"], text, critique, draft=result.draft),
    }


def score_case(item: dict, *, baseline, generic, critic_only, shield) -> dict:
    arms = {
        "baseline": score_arm(item, baseline),
        "generic": score_arm(item, generic),
        "critic_only": score_arm(item, critic_only),
        "shield": score_arm(item, shield),
    }
    drafts = {arm["draft"] for arm in arms.values()}
    return {
        "id": item["id"],
        "kind": item["kind"],
        "draft": shield.draft,
        "shared_draft": len(drafts) == 1,
        "arms": arms,
        "retrieved_ids": shield.retrieved_ids,
        "survivorship_risk": arms["shield"]["survivorship_risk"],
        "confidence_adjustment": arms["shield"]["confidence_adjustment"],
        "missing_data_language": arms["shield"]["missing_data_language"],
        "used_store_ids": arms["shield"]["used_store_ids"],
        "baseline_chars": arms["baseline"]["chars"],
        "shielded_chars": arms["shield"]["chars"],
        "pass": arms["shield"]["pass"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AbsenceCritic Phase 0 eval")
    parser.add_argument("--provider", choices=("fixture", "openai"), default="fixture")
    parser.add_argument("--queries", type=Path, default=ROOT / "eval" / "queries.yaml")
    parser.add_argument(
        "--jsonl",
        type=Path,
        help="Append each case as JSONL as it finishes (keeps partial results)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1,
        help="Repeat each query this many times (live variance; fixtures are deterministic)",
    )
    args = parser.parse_args(argv)
    if args.samples < 1:
        parser.error("--samples must be >= 1")
    load_repo_env()

    provider = (
        FixtureLLM(ROOT / "eval" / "fixtures" / "responses.yaml")
        if args.provider == "fixture"
        else OpenAICompat()
    )
    store = YamlStore(ROOT / "data" / "non_survivors")
    jsonl = args.jsonl.open("w", encoding="utf-8") if args.jsonl else None
    samples: list[list[dict]] = []
    try:
        for _ in range(args.samples):
            rows = []
            for item in load_queries(args.queries):
                q = item["query"]
                try:
                    draft = provider.generate(query=q)
                    baseline = run(
                        q, provider=provider, store=store, shield=False, draft=draft
                    )
                    generic = generic_arm(q, draft, generator=provider)
                    critic_only = run(
                        q,
                        provider=provider,
                        store=store,
                        shield=True,
                        retrieve_k=0,
                        draft=draft,
                    )
                    shielded = run(
                        q, provider=provider, store=store, shield=True, draft=draft
                    )
                    row = score_case(
                        item,
                        baseline=baseline,
                        generic=generic,
                        critic_only=critic_only,
                        shield=shielded,
                    )
                except Exception as exc:
                    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                        raise
                    row = {
                        "id": item.get("id"),
                        "kind": item.get("kind"),
                        "pass": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                    raw = getattr(exc, "raw", None)
                    if raw is not None:
                        row["raw_critique"] = raw[:RAW_CRITIQUE_LIMIT]
                rows.append(row)
                if jsonl is not None:
                    jsonl.write(json.dumps(row, ensure_ascii=False) + "\n")
                    jsonl.flush()
            samples.append(rows)
    finally:
        if jsonl is not None:
            jsonl.close()

    rows = samples[0]
    n_pass = sum(1 for r in rows if r.get("pass") and "error" not in r)
    n_error = sum(1 for r in rows if "error" in r)
    n_fail = sum(1 for r in rows if not r.get("pass") and "error" not in r)
    payload = {
        "passed": n_pass,
        "failed": n_fail,
        "errored": n_error,
        "total": len(rows),
        "samples": args.samples,
        "arms": _arm_summary(samples),
        "arm_deltas_meaningful": args.provider != "fixture",
        "cases": rows,
    }
    if args.provider == "fixture":
        payload["note"] = FIXTURE_NOTE
    if args.samples > 1:
        payload["sample_cases"] = samples
    print(json.dumps(payload, indent=2))
    return 0 if n_fail == 0 and n_error == 0 else 1


def _arm_summary(samples: list[list[dict]]) -> dict:
    out: dict[str, dict] = {}
    for name in ARMS:
        rates = []
        for rows in samples:
            scored = [
                row["arms"][name]["pass"]
                for row in rows
                if "error" not in row and "arms" in row
            ]
            if scored:
                rates.append(sum(1 for ok in scored if ok) / len(scored))
        if not rates:
            out[name] = {"mean": None, "spread": None}
            continue
        mean = sum(rates) / len(rates)
        spread = max(rates) - min(rates)
        out[name] = {"mean": mean, "spread": spread}
        controls = [
            row["arms"][name]["unneeded_caveat"]
            for rows in samples
            for row in rows
            if "arms" in row and row.get("kind") == "control"
        ]
        out[name]["control_false_alarm_rate"] = (
            sum(1 for flagged in controls if flagged) / len(controls) if controls else None
        )
    return out


if __name__ == "__main__":
    raise SystemExit(main())

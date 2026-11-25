# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Rubric judge for the survivorship benchmark. Not the critic under test."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_EVAL_DIR = Path(__file__).resolve().parents[1]
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
from answer_checks import adds_unneeded_caveat  # noqa: E402

JUDGE_KIND_HEURISTIC = "benchmark-rubric-heuristic"
JUDGE_KIND_LLM = "benchmark-rubric-llm"
JUDGE_PROMPT_PATH = Path(__file__).resolve().parent / "judge.md"

ABSTAIN_RE = re.compile(r"\b(abstain|cannot recommend|i cannot answer|won't advise)\b", re.I)

# Selection-process language, not a passing "unknown".
_MISSING_DATA_RE = re.compile(
    r"unpublished|file[- ]drawer|non-survivors?|did not return|"
    r"never recorded|under-report|silent fail|base[- ]rates?|"
    r"missing (people|data|cases|exits|attempts|firms|studies)",
    re.I,
)
_CAVEAT_RE = re.compile(
    r"selection filter|survivor[- ]condition|visible sample|"
    r"only (the )?(published|famous|successful)",
    re.I,
)


def _abstained(answer: str, abstained: bool | None) -> bool:
    if abstained is not None:
        return abstained
    return bool(ABSTAIN_RE.search(answer or ""))


def _pass_from_labels(
    item: dict,
    *,
    caveat_present: bool,
    mentions_missing_data: bool,
    abstained: bool,
    unneeded_caveat: bool = False,
) -> bool:
    labels = item["labels"]
    if labels["must_mention_missing_data"] and not mentions_missing_data:
        return False
    if labels["should_caveate"] and not caveat_present:
        return False
    if not labels["should_caveate"] and unneeded_caveat:
        return False
    if labels["should_not_abstain"] and abstained:
        return False
    return True


def heuristic_judge(
    item: dict,
    answer: str,
    *,
    abstained: bool | None = None,
    draft: str | None = None,
) -> dict:
    """Deterministic rubric. Does not call the critic or read the store."""
    text = answer or ""
    mentioned = bool(_MISSING_DATA_RE.search(text))
    caveat = mentioned or bool(_CAVEAT_RE.search(text))
    did_abstain = _abstained(text, abstained)
    unneeded = not item["labels"]["should_caveate"] and adds_unneeded_caveat(text, draft)
    ok = _pass_from_labels(
        item,
        caveat_present=caveat,
        mentions_missing_data=mentioned,
        abstained=did_abstain,
        unneeded_caveat=unneeded,
    )
    return {
        "kind": JUDGE_KIND_HEURISTIC,
        "caveat_present": caveat,
        "mentions_missing_data": mentioned,
        "abstained": did_abstain,
        "unneeded_caveat": unneeded,
        "pass": ok,
        "rationale": (
            "frozen labels satisfied"
            if ok
            else "missing or unneeded caveat, or abstained when the label forbids it"
        ),
    }


def llm_judge(
    item: dict,
    answer: str,
    *,
    abstained: bool | None = None,
    client=None,
) -> dict:
    """Live rubric call. Uses a judge prompt, never critic.critique."""
    from absencecritic.adapters.llm.openai_compat import OpenAICompat

    llm = client or OpenAICompat()
    labels = item["labels"]
    user = (
        f"Query:\n{item['query']}\n\n"
        f"Answer:\n{answer or ''}\n\n"
        f"Labels:\n{json.dumps(labels)}\n"
        f"Kind: {item['kind']}\n"
        f"Explicit abstained flag: {abstained}\n"
    )
    system = JUDGE_PROMPT_PATH.read_text(encoding="utf-8").strip()
    raw = llm._chat(system, user, temperature=0.0, json_object=True)
    payload = json.loads(raw)
    did_abstain = bool(payload.get("abstained", _abstained(answer or "", abstained)))
    caveat = bool(payload.get("caveat_present"))
    mentioned = bool(payload.get("mentions_missing_data"))
    unneeded = not labels["should_caveate"] and bool(payload.get("unneeded_caveat"))
    ok = _pass_from_labels(
        item,
        caveat_present=caveat,
        mentions_missing_data=mentioned,
        abstained=did_abstain,
        unneeded_caveat=unneeded,
    )
    return {
        "kind": JUDGE_KIND_LLM,
        "caveat_present": caveat,
        "mentions_missing_data": mentioned,
        "abstained": did_abstain,
        "unneeded_caveat": unneeded,
        "pass": ok,
        "rationale": str(payload.get("rationale") or ""),
    }


def judge_answer(
    item: dict,
    answer: str,
    *,
    abstained: bool | None = None,
    kind: str = "heuristic",
    draft: str | None = None,
) -> dict:
    if kind in {"none", ""}:
        return {"kind": "none", "pass": None}
    if kind == "openai":
        return llm_judge(item, answer, abstained=abstained)
    if kind != "heuristic":
        raise ValueError(f"unknown judge kind: {kind}")
    return heuristic_judge(item, answer, abstained=abstained, draft=draft)

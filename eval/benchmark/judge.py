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
from answer_checks import SURVIVORSHIP_CAVEAT_RE, adds_unneeded_caveat  # noqa: E402

JUDGE_KIND_HEURISTIC = "benchmark-rubric-heuristic"
JUDGE_KIND_LLM = "benchmark-rubric-llm"
JUDGE_PROMPT_PATH = Path(__file__).resolve().parent / "judge.md"

ABSTAIN_RE = re.compile(r"\b(abstain|cannot recommend|i cannot answer|won't advise)\b", re.I)

# Selection-process language, not a passing "unknown".
_MISSING_DATA_RE = re.compile(
    r"unpublished|file[- ]drawer|non-survivors?|did not return|"
    r"never (recorded|published|reported|written up)|"
    r"(was|were) not (published|reported|recorded)|under-report|silent fail|base[- ]rates?|"
    r"missing (people|data|cases|exits|attempts|firms|studies)",
    re.I,
)
_CAVEAT_RE = re.compile(
    r"selection filter|survivor[- ]condition|visible sample|survivorship|"
    r"only (the )?(published|famous|successful)",
    re.I,
)

# Graded rubric for items that should caveat. Each key is one point.
RUBRIC_KEYS = ("specific_filter", "concrete_evidence", "settling_data", "no_invented_sources")
_PARAGRAPH_RE = re.compile(r"\n\s*\n")
_CAVEAT_CUE_RE = re.compile(
    r"are visible|outside the sample|(did not|didn't|never) (survive|make it|publish|report)|"
    r"remains? unknown|cannot show|missing|survivor|selection|left (early|earlier)|"
    r"(failed|closed|cancelled|abandoned) (ones|cases|attempts|firms|funds)",
    re.I,
)
_WORD_RE = re.compile(r"[a-z][a-z'-]{3,}")
_QUERY_STOP = frozenset(
    "which what when where should would could does that this these those with from "
    "have has only based still because their there they them about after before same "
    "into than then more most best work works worked make made using used every each "
    "some other people team teams just like also been being were will".split()
)
_EVIDENCE_RE = re.compile(
    r"\d|percent|\bhalf\b|\bmajority\b|\bone in (two|three|four|five|ten)\b|"
    r"\b(two|three|four|five|six|seven|eight|nine|ten)[- ]thirds?\b",
    re.I,
)
_SETTLING_RE = re.compile(
    r"\b(compare|comparing|comparison|track|tracking|collect|denominator|"
    r"control group|full (list|cohort|record|population|set)|"
    r"including (those|the ones|failures|the failures)|all (the )?\w+ that (tried|started|applied|launched)|"
    r"before (deciding|concluding|drawing)|ask for|look for data)\b",
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


def rubric_score(rubric: dict | None) -> float | None:
    """Fraction of scored rubric points; keys set to None were not scored."""
    if not rubric:
        return None
    scored = [bool(v) for v in rubric.values() if v is not None]
    return sum(scored) / len(scored) if scored else None


def _content_words(text: str) -> set[str]:
    words = (w.rstrip("s") for w in _WORD_RE.findall(text.lower()))
    return {w for w in words if len(w) >= 4 and w not in _QUERY_STOP}


def heuristic_rubric(item: dict, answer: str) -> dict | None:
    """Deterministic rubric on caveat paragraphs. Cannot tell invented sources, so leaves them None."""
    if not item["labels"]["should_caveate"]:
        return None
    caveats = [
        p for p in _PARAGRAPH_RE.split(answer or "")
        if any(
            rx.search(p)
            for rx in (_MISSING_DATA_RE, _CAVEAT_RE, SURVIVORSHIP_CAVEAT_RE, _CAVEAT_CUE_RE)
        )
    ]
    query_words = _content_words(item["query"])
    return {
        "specific_filter": any(query_words & _content_words(p) for p in caveats),
        "concrete_evidence": any(_EVIDENCE_RE.search(p) for p in caveats),
        "settling_data": bool(_SETTLING_RE.search(answer or "")),
        "no_invented_sources": None,
    }


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
    rubric = heuristic_rubric(item, text)
    return {
        "kind": JUDGE_KIND_HEURISTIC,
        "caveat_present": caveat,
        "mentions_missing_data": mentioned,
        "abstained": did_abstain,
        "unneeded_caveat": unneeded,
        "rubric": rubric,
        "rubric_score": rubric_score(rubric),
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
    rubric = None
    if labels["should_caveate"]:
        raw_rubric = payload.get("rubric") or {}
        rubric = {key: bool(raw_rubric.get(key)) for key in RUBRIC_KEYS}
    return {
        "kind": JUDGE_KIND_LLM,
        "caveat_present": caveat,
        "mentions_missing_data": mentioned,
        "abstained": did_abstain,
        "unneeded_caveat": unneeded,
        "rubric": rubric,
        "rubric_score": rubric_score(rubric),
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

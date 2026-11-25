# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from absencecritic.domain.models import (
    MAX_AUTHOR_PRIOR_CONFIDENCE,
    StoreCollection,
    StoreEntry,
    StoreEvidence,
    StoreStatus,
)

INGEST_FILENAME = "ingested.yaml"
FEEDBACK_DIRNAME = "feedback"
PENDING_FILENAME = "pending.yaml"
_INGEST_HEADER = """\
# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0
#
# schema_version: 1
# Curated Phase 1 ingest. Written by YamlStore.add; seed notes stay in
# other YAML files in this directory.
"""

_TOKEN = re.compile(r"[a-z0-9]+")
# Function words and filler that match almost any entry; overlap on them is noise.
_STOP = frozenset(
    """
    a about above after again against all also although always am an and any are
    around as at base based be because been before being below between both but by can could
    find found work works worked working
    did do does doing done down during each either else even ever every few for
    from further get gets getting give given go goes going got had has have having
    he her here hers herself him himself his how however i if in into is it its
    itself just let like look looks made make makes many may me might more most
    much must my myself need needs never no nor not now of off often on once one
    only onto or other others our ours ourselves out over own per quite rather
    really said same say says see seem seems several shall she should since so
    some something still such than that the their theirs them themselves then
    there these they thing things this those though through thus to too toward
    under until up upon us use used using very via was way we well were what
    whatever when where whether which while who whom whose why will with within
    without would yet you your yours yourself
    """.split()
)


def _write_entries(
    path: Path, entries: list[StoreEntry], header: str = _INGEST_HEADER
) -> None:
    payload = [
        e.model_dump(mode="json", exclude={"source_path"}, exclude_none=True)
        for e in entries
    ]
    body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    path.write_text(header + "\n" + body, encoding="utf-8")


_METHOD_TOKENS = frozenset(
    {
        "abraham",
        "armor",
        "bias",
        "critic",
        "insight",
        "module",
        "quote",
        "shield",
        "survivor",
        "survivors",
        "survivorship",
        "wald",
    }
)
_ADVICE_CUES = frozenset(
    {
        "advice",
        "always",
        "best",
        "founder",
        "founders",
        "guaranteed",
        "launch",
        "launched",
        "launching",
        "should",
        "success",
        "successful",
        "tips",
        "treatment",
        "tricks",
        "work",
        "works",
    }
)
_MIN_OVERLAP = 2
_SCORE_RATIO = 0.5
_MIN_SCORE = 0.05


def _words(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def _singular(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def retrievable(entry: StoreEntry) -> bool:
    """Pending notes and unaccepted feedback stay out of retrieval."""
    if entry.status is StoreStatus.pending:
        return False
    if (
        entry.collection is StoreCollection.feedback
        and entry.status is not StoreStatus.accepted
    ):
        return False
    return True


def tokenize(text: str) -> set[str]:
    return {_singular(t) for t in _words(text) if t not in _STOP and len(t) > 1}


def _related(left: str, right: str) -> bool:
    if left == right:
        return True
    if min(len(left), len(right)) < 5:
        return False
    return left.startswith(right) or right.startswith(left)


def _domain_hit(domain: str, content: set[str]) -> bool:
    domain_tokens = tokenize(domain.replace("_", " "))
    return any(
        _related(dt, ct) for dt in domain_tokens for ct in content
    )


def _query_content(query: str, draft: str) -> set[str]:
    q = tokenize(query)
    meta = bool(q & {"wald", "abraham", "quote"}) and not (_words(query) & _ADVICE_CUES)
    if meta:
        return q - _METHOD_TOKENS
    combined = tokenize(f"{query} {draft}")
    content = combined - _METHOD_TOKENS
    if content:
        return content
    if _words(draft) & _ADVICE_CUES:
        return combined
    return set()


def _anchored(query_tokens: set[str], bag: set[str], domain: str, id_tokens: set[str]) -> bool:
    """The question itself, not only the draft, must touch the entry."""
    if query_tokens & id_tokens or _domain_hit(domain, query_tokens):
        return True
    return any(_related(qt, bt) for qt in query_tokens for bt in bag)


def load_entries(path: Path) -> list[StoreEntry]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        raw = yaml.safe_load(text)
    elif path.suffix.lower() == ".jsonl":
        raw = [json.loads(line) for line in text.splitlines() if line.strip()]
    elif path.suffix.lower() == ".json":
        raw = json.loads(text)
    else:
        return []
    if raw is None:
        return []
    if isinstance(raw, dict):
        if "entries" in raw:
            raw = raw["entries"]
        else:
            raw = [raw]
    if not isinstance(raw, list):
        raise ValueError(f"Expected a list of entries in {path}")
    entries = []
    for item in raw:
        entry = StoreEntry.model_validate(item)
        entry.source_path = str(path)
        entries.append(entry)
    return entries


class YamlStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.entries: list[StoreEntry] = []
        self._bags: list[set[str]] = []
        self.reload()

    def _iter_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.directory.iterdir():
            # Nested private/ is gitignored and not retrieved. Org memory is a
            # separate ABSENCECRITIC_STORE directory, not this folder.
            if path.name == "private" and path.is_dir():
                continue
            if path.suffix.lower() in {".yaml", ".yml", ".json", ".jsonl"}:
                files.append(path)
        extra = self.directory / FEEDBACK_DIRNAME
        if extra.is_dir():
            for path in extra.iterdir():
                if path.suffix.lower() in {".yaml", ".yml", ".json", ".jsonl"}:
                    files.append(path)
        return sorted(files)

    def reload(self) -> None:
        self.entries = []
        if not self.directory.exists():
            raise FileNotFoundError(f"Non-Survivor Store not found: {self.directory}")
        for path in self._iter_files():
            self.entries.extend(load_entries(path))
        self._bags = [
            tokenize(
                " ".join(
                    [
                        e.id,
                        e.domain,
                        e.selection_process,
                        e.survivor_pattern,
                        e.non_survivor_evidence,
                        e.provenance,
                    ]
                )
            )
            for e in self.entries
        ]

    def retrieve(self, query: str, draft: str = "", k: int = 5) -> list[tuple[StoreEntry, float]]:
        content = _query_content(query, draft)
        if not content:
            return []
        query_tokens = tokenize(query) - _METHOD_TOKENS
        scored: list[tuple[int, float]] = []
        for i, bag in enumerate(self._bags):
            entry = self.entries[i]
            if not retrievable(entry):
                continue
            overlap = content & bag
            id_tokens = {
                tok for tok in tokenize(entry.id) - _METHOD_TOKENS if len(tok) >= 4
            }
            id_hit = bool(id_tokens & content)
            domain_hit = _domain_hit(entry.domain, content)
            if not overlap and not domain_hit and not id_hit:
                continue
            if len(overlap) < _MIN_OVERLAP and not domain_hit and not id_hit:
                continue
            if not _anchored(query_tokens, bag, entry.domain, id_tokens):
                continue
            score = len(overlap) / len(content)
            if domain_hit:
                score += 0.15
            if id_hit:
                score += 0.05
            scored.append((i, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        if not scored:
            return []
        floor = max(scored[0][1] * _SCORE_RATIO, _MIN_SCORE)
        kept = [(i, score) for i, score in scored if score >= floor]
        return [(self.entries[i], score) for i, score in kept[:k]]

    def add(self, entry: StoreEntry) -> StoreEntry:
        """Append a validated entry to ingested.yaml. Retrieve-only StorePort is unchanged."""
        validated = StoreEntry.model_validate(
            entry.model_dump(exclude={"source_path"}, exclude_none=True)
        )
        if not validated.provenance.strip():
            raise ValueError("provenance is required")
        if (
            validated.evidence is StoreEvidence.author_prior
            and validated.confidence > MAX_AUTHOR_PRIOR_CONFIDENCE
        ):
            raise ValueError(
                f"author_prior confidence must be <= {MAX_AUTHOR_PRIOR_CONFIDENCE}"
            )
        if any(existing.id == validated.id for existing in self.entries):
            raise ValueError(f"duplicate store id: {validated.id}")
        if not validated.ingested_at:
            stamped = (
                datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            )
            validated = validated.model_copy(update={"ingested_at": stamped})
        path = self.directory / INGEST_FILENAME
        current = load_entries(path) if path.exists() else []
        current.append(validated)
        _write_entries(path, current)
        self.reload()
        return validated

    def format_hits(self, hits: list[tuple[StoreEntry, float]]) -> str:
        if not hits:
            return "(none retrieved)"
        blocks = []
        for entry, score in hits:
            blocks.append(
                "\n".join(
                    [
                        f"id: {entry.id}",
                        f"domain: {entry.domain}",
                        f"retrieval_score: {score:.3f}",
                        f"selection_process: {entry.selection_process}",
                        f"survivor_pattern: {entry.survivor_pattern}",
                        f"non_survivor_evidence: {entry.non_survivor_evidence}",
                        f"confidence: {entry.confidence}",
                        f"evidence: {entry.evidence.value}",
                        f"provenance: {entry.provenance}",
                    ]
                )
            )
        return "\n---\n".join(blocks)

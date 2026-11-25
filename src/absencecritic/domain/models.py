# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ConfidenceAdjustment(str, Enum):
    lower = "lower"
    abstain = "abstain"
    seek_more_data = "seek_more_data"
    unchanged = "unchanged"


class StoreCollection(str, Enum):
    seed = "seed"
    catalog = "catalog"
    feedback = "feedback"


class StoreStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"


class StoreEvidence(str, Enum):
    cited = "cited"
    author_prior = "author_prior"


class StoreKind(str, Enum):
    evidence = "evidence"
    design_failure = "design_failure"


class BlockerStatus(str, Enum):
    active = "active"
    expired = "expired"
    unknown = "unknown"


AUTHOR_PRIOR_PREFIX = "author prior"
MAX_AUTHOR_PRIOR_CONFIDENCE = 0.5


class NonSurvivorHit(BaseModel):
    id: str
    summary: str
    provenance: str
    confidence: float = Field(ge=0.0, le=1.0)


class Critique(BaseModel):
    selection_filter: str
    visible_damage: list[str] = Field(default_factory=list)
    empty_regions: list[str] = Field(default_factory=list)
    non_survivors: list[NonSurvivorHit] = Field(default_factory=list)
    unknown_lethality: list[str] = Field(default_factory=list)
    survivorship_risk: float = Field(ge=0.0, le=1.0)
    confidence_adjustment: ConfidenceAdjustment
    caveats: list[str] = Field(default_factory=list)
    missing_categories: list[str] = Field(default_factory=list)
    suggested_queries: list[str] = Field(default_factory=list)


class RevivableHit(BaseModel):
    id: str
    summary: str
    provenance: str
    confidence: float = Field(ge=0.0, le=1.0)
    death_reason: str = ""
    blocker: str = ""
    blocker_status: BlockerStatus = BlockerStatus.unknown
    revival_rationale: str = ""


class DesignCritique(Critique):
    assumptions: list[str] = Field(default_factory=list)
    untried_regions: list[str] = Field(default_factory=list)
    revivable_entries: list[RevivableHit] = Field(default_factory=list)


class DesignCandidate(BaseModel):
    id: str
    design: str
    rationale: str = ""


class DesignScore(BaseModel):
    candidate_id: str
    novelty: float = Field(ge=0.0, le=1.0)
    feasibility: float = Field(ge=0.0, le=1.0)
    usefulness: float = Field(ge=0.0, le=1.0)
    rationale_quality: float = Field(ge=0.0, le=1.0)
    invented_source: bool = False
    invented_dead_design: bool = False
    rank: int = Field(ge=1)
    rationale: str = ""


class DesignScoreSheet(BaseModel):
    scores: list[DesignScore] = Field(default_factory=list)


class StoreEntry(BaseModel):
    id: str
    domain: str
    selection_process: str
    survivor_pattern: str
    non_survivor_evidence: str
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: str
    collection: StoreCollection = StoreCollection.seed
    status: StoreStatus = StoreStatus.accepted
    evidence: StoreEvidence = StoreEvidence.cited
    kind: StoreKind = StoreKind.evidence
    death_reason: Optional[str] = None
    blocker: Optional[str] = None
    blocker_status: Optional[BlockerStatus] = None
    event_date: Optional[str] = None
    source_url: Optional[str] = None
    ingested_at: Optional[str] = None
    source_path: Optional[str] = None

    @model_validator(mode="after")
    def _author_prior_from_provenance(self) -> "StoreEntry":
        if self.provenance.strip().lower().startswith(AUTHOR_PRIOR_PREFIX):
            self.evidence = StoreEvidence.author_prior
        return self


@dataclass
class PipelineResult:
    query: str
    draft: str
    retrieved_ids: list[str] = field(default_factory=list)
    critique: Optional[Critique] = None
    final: str = ""
    shielded: bool = True


@dataclass
class GenerativeResult:
    brief: str
    draft: str
    drafts: list[str] = field(default_factory=list)
    retrieved_ids: list[str] = field(default_factory=list)
    critique: Optional[DesignCritique] = None
    candidates: list[DesignCandidate] = field(default_factory=list)
    scores: Optional[DesignScoreSheet] = None
    ranked: list[DesignCandidate] = field(default_factory=list)
    store_used: bool = False

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

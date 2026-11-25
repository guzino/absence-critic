# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""AbsenceCritic: a survivorship-bias shield for language models."""

from absencecritic.application.generative import run_generative
from absencecritic.application.loop import run, score
from absencecritic.domain.models import (
    Critique,
    DesignCritique,
    GenerativeResult,
    PipelineResult,
    StoreEntry,
)

__all__ = [
    "Critique",
    "DesignCritique",
    "GenerativeResult",
    "PipelineResult",
    "StoreEntry",
    "run",
    "run_generative",
    "score",
]
__version__ = "0.1.5"

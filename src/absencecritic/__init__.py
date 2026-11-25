# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""AbsenceCritic: a survivorship-bias shield for language models."""

from absencecritic.application.loop import run, score
from absencecritic.domain.models import Critique, PipelineResult, StoreEntry

__all__ = ["Critique", "PipelineResult", "StoreEntry", "run", "score"]
__version__ = "0.1.1"

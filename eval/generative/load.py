# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def load_briefs() -> list[dict]:
    raw = yaml.safe_load((ROOT / "briefs.yaml").read_text(encoding="utf-8"))
    return list(raw["briefs"])


def load_splits() -> dict:
    return yaml.safe_load((ROOT / "splits.yaml").read_text(encoding="utf-8"))

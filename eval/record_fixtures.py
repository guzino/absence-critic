# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

"""Record live or fixture Wald triples into eval/fixtures/responses.yaml."""

from __future__ import annotations

import argparse
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
from absencecritic.paths import default_fixture_path, default_store_dir  # noqa: E402

QUERIES_PATH = ROOT / "eval" / "queries.yaml"
_HEADER = """\
# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0
#
# Recorded draft / critique / revision triples. Tests and eval use these
# so CI needs no API keys. Regenerated with:
#   python eval/record_fixtures.py --provider openai --out eval/fixtures/responses.yaml
"""


def load_queries(path: Path) -> list[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [str(item["query"]).strip() for item in raw["queries"]]


def record_rows(queries: list[str], *, provider: object, store: YamlStore) -> list[dict]:
    rows: list[dict] = []
    for query in queries:
        result = run(query, provider=provider, store=store, shield=True)
        if result.critique is None:
            raise RuntimeError(f"no critique for {query!r}")
        rows.append(
            {
                "query": query,
                "draft": result.draft,
                "critique": result.critique.model_dump(mode="json"),
                "revision": result.final,
            }
        )
    return rows


def write_responses(path: Path, rows: list[dict]) -> None:
    body = yaml.safe_dump(rows, sort_keys=False, allow_unicode=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_HEADER + "\n" + body, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record Wald triples for fixture eval. Live calls need OPENAI_API_KEY."
    )
    parser.add_argument("--provider", choices=("fixture", "openai"), default="openai")
    parser.add_argument("--queries", type=Path, default=QUERIES_PATH)
    parser.add_argument("--out", type=Path, default=default_fixture_path())
    args = parser.parse_args(argv)
    load_repo_env()
    provider = (
        FixtureLLM(default_fixture_path())
        if args.provider == "fixture"
        else OpenAICompat()
    )
    store = YamlStore(default_store_dir())
    rows = record_rows(load_queries(args.queries), provider=provider, store=store)
    write_responses(args.out, rows)
    print(args.out.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from absencecritic.adapters.llm.fixture import FixtureLLM, FixtureQueryNotFound
from absencecritic.adapters.llm.local import LocalCritic
from absencecritic.adapters.llm.openai_compat import (
    LLMError,
    MissingAPIKey,
    OpenAICompat,
    design_openai_compat,
)
from absencecritic.adapters.store.catalog import ingest_catalog
from absencecritic.adapters.store.feedback import accept_feedback, queue_feedback
from absencecritic.adapters.store.ingest import ingest_yaml
from absencecritic.adapters.store.embedding import (
    EMBED_UPLOAD_WARNING,
    EmbedError,
    EmbeddingStore,
    HashEmbedder,
    MissingEmbedKey,
    OpenAIEmbedder,
)
from absencecritic.adapters.store.yaml_store import YamlStore
from absencecritic.application.generative import run_generative
from absencecritic.application.loop import CritiqueParseError, run, score
from absencecritic.envfile import load_repo_env
from absencecritic.paths import (
    default_fixture_path,
    default_generative_fixture_path,
    default_store_dir,
)


def _llm(name: str):
    if name == "fixture":
        return FixtureLLM(default_fixture_path())
    if name == "openai":
        return OpenAICompat()
    raise ValueError(f"Unknown provider: {name}")


def _design_llm(name: str):
    if name == "fixture":
        return FixtureLLM(default_generative_fixture_path())
    if name == "openai":
        return design_openai_compat()
    raise ValueError(f"Unknown provider: {name}")


def _store(args):
    if args.retrieve == "embedding":
        print(EMBED_UPLOAD_WARNING, file=sys.stderr)
        return EmbeddingStore(args.store, OpenAIEmbedder())
    if args.retrieve == "hash":
        return EmbeddingStore(args.store, HashEmbedder())
    return YamlStore(args.store)


def _critic(name: str, generator):
    if name == "prompt":
        return generator
    if name == "local":
        return LocalCritic()
    raise ValueError(f"Unknown critic: {name}")


def _default_provider_name() -> str:
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "fixture"


def _ingest_cmd(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="absencecritic ingest",
        description="Validate and append curated Non-Survivor Store YAML.",
    )
    parser.add_argument("file", type=Path, help="YAML/JSONL of StoreEntry records or a catalog")
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Treat FILE as a frozen citable catalog (requires source_url)",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=default_store_dir(),
        help="Directory of Non-Survivor Store YAML/JSONL files",
    )
    args = parser.parse_args(argv)
    ids = (
        ingest_catalog(args.store, args.file)
        if args.catalog
        else ingest_yaml(args.store, args.file)
    )
    for entry_id in ids:
        print(entry_id)
    return 0


def _feedback_cmd(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="absencecritic feedback",
        description="Queue or accept user failure notes (pending until accepted).",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="YAML of StoreEntry records to queue as pending",
    )
    parser.add_argument(
        "--accept",
        metavar="ID",
        help="Mark a pending feedback id as accepted (then it can retrieve)",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=default_store_dir(),
        help="Directory of Non-Survivor Store YAML/JSONL files",
    )
    args = parser.parse_args(argv)
    if args.accept:
        accept_feedback(args.store, args.accept)
        print(args.accept)
        return 0
    if args.file is None:
        parser.error("provide a YAML file or --accept ID")
    for entry_id in queue_feedback(args.store, args.file):
        print(entry_id)
    return 0


def _design_cmd(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="absencecritic design",
        description="Gap-directed designs from a brief. Experimental; not the shield.",
    )
    parser.add_argument("brief", help="Design brief")
    parser.add_argument(
        "--no-store",
        action="store_true",
        help="Critic-only arm: no store retrieval",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print the full generative result as JSON",
    )
    parser.add_argument(
        "--show-critique",
        action="store_true",
        help="Print the design critique after the ranked designs",
    )
    parser.add_argument(
        "--provider",
        choices=("fixture", "openai"),
        default=_default_provider_name(),
        help="LLM backend (default: fixture unless OPENAI_API_KEY is set)",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=default_store_dir(),
        help="Directory of Non-Survivor Store YAML/JSONL files",
    )
    parser.add_argument("--debug", action="store_true", help="Show full provider tracebacks")
    args = parser.parse_args(argv)
    try:
        store = YamlStore(args.store)
        provider = _design_llm(args.provider)
        result = run_generative(
            args.brief,
            provider=provider,
            store=store,
            use_store=not args.no_store,
        )
    except (FixtureQueryNotFound, MissingAPIKey, LLMError, CritiqueParseError) as error:
        if args.debug:
            raise
        if isinstance(error, FixtureQueryNotFound):
            message = (
                "Fixture design mode only supports recorded briefs. "
                "Use --provider openai with OPENAI_API_KEY for your own brief."
            )
        elif isinstance(error, MissingAPIKey):
            message = "Set OPENAI_API_KEY for the live provider or choose --provider fixture."
        elif isinstance(error, LLMError):
            status = f" (HTTP {error.status})" if error.status is not None else ""
            message = f"The live provider request failed{status}. Check the provider configuration."
        else:
            message = "The design loop returned an invalid reply. Try again."
        print(f"Error: {message}", file=sys.stderr)
        return 1

    if args.as_json:
        payload = {
            "brief": result.brief,
            "draft": result.draft,
            "drafts": result.drafts,
            "retrieved_ids": result.retrieved_ids,
            "critique": result.critique.model_dump(mode="json") if result.critique else None,
            "candidates": [c.model_dump(mode="json") for c in result.candidates],
            "scores": result.scores.model_dump(mode="json") if result.scores else None,
            "ranked": [c.model_dump(mode="json") for c in result.ranked],
            "store_used": result.store_used,
        }
        print(json.dumps(payload, indent=2))
        return 0
    if not result.ranked:
        print(result.draft)
    else:
        for index, candidate in enumerate(result.ranked, start=1):
            print(f"{index}. {candidate.design}")
            if candidate.rationale:
                print(f"   {candidate.rationale}")
            if index < len(result.ranked):
                print()
    if args.show_critique and result.critique is not None:
        print("\n--- critique ---\n")
        print(json.dumps(result.critique.model_dump(mode="json"), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    load_repo_env()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "ingest":
        return _ingest_cmd(argv[1:])
    if argv and argv[0] == "feedback":
        return _feedback_cmd(argv[1:])
    if argv and argv[0] == "design":
        return _design_cmd(argv[1:])
    parser = argparse.ArgumentParser(
        prog="absencecritic",
        description="Run the AbsenceCritic Wald loop: draft → critic → revise.",
    )
    parser.add_argument("query", help="User question")
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Critique an existing draft; do not generate or revise",
    )
    parser.add_argument(
        "--draft-file",
        type=Path,
        help="Draft text for --judge",
    )
    parser.add_argument(
        "--no-shield",
        action="store_true",
        help="Return the primary draft only (baseline)",
    )
    parser.add_argument(
        "--show-critique",
        action="store_true",
        help="Print the structured critique after the answer",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print the full pipeline result as JSON",
    )
    parser.add_argument(
        "--provider",
        choices=("fixture", "openai"),
        default=_default_provider_name(),
        help="LLM backend (default: fixture unless OPENAI_API_KEY is set)",
    )
    parser.add_argument(
        "--critic",
        choices=("prompt", "local"),
        default="prompt",
        help="Critic backend (default: same prompted model as --provider)",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=default_store_dir(),
        help="Directory of Non-Survivor Store YAML/JSONL files",
    )
    parser.add_argument(
        "--retrieve",
        choices=("keyword", "embedding", "hash"),
        default="keyword",
        help=(
            "How the critic finds store notes (default: keyword). "
            "embedding sends the question and the full text of every store note "
            "to the embeddings endpoint. hash stays on this machine and only "
            "matches shared words."
        ),
    )
    parser.add_argument("--debug", action="store_true", help="Show full provider tracebacks")
    args = parser.parse_args(argv)
    if args.judge and args.no_shield:
        parser.error("--judge cannot be combined with --no-shield")
    if args.judge and args.draft_file is None:
        parser.error("--judge requires --draft-file")
    if args.draft_file is not None and not args.judge:
        parser.error("--draft-file requires --judge")

    try:
        store = _store(args)
        generator = _llm(args.provider)
        critic = _critic(args.critic, generator)
        if args.judge:
            result = score(
                args.query,
                args.draft_file.read_text(encoding="utf-8"),
                critic=critic,
                store=store,
            )
        else:
            result = run(
                args.query,
                generator=generator,
                critic=critic,
                store=store,
                shield=not args.no_shield,
            )
    except (FixtureQueryNotFound, MissingAPIKey, MissingEmbedKey, EmbedError, LLMError, CritiqueParseError) as error:
        if args.debug:
            raise
        if isinstance(error, FixtureQueryNotFound):
            message = (
                'Fixture mode only supports recorded demo questions. Try "What is 2+2?", '
                "or use --provider openai with OPENAI_API_KEY for your own question."
            )
        elif isinstance(error, MissingAPIKey):
            message = "Set OPENAI_API_KEY for the live provider or choose --provider fixture."
        elif isinstance(error, MissingEmbedKey):
            message = (
                "Set ABSENCECRITIC_EMBED_API_KEY (or OPENAI_API_KEY) for embedding "
                "retrieval, or choose --retrieve keyword or --retrieve hash. "
                "Embedding retrieval sends every store note to the embeddings endpoint."
            )
        elif isinstance(error, EmbedError):
            status = f" (HTTP {error.status})" if error.status is not None else ""
            message = f"The embeddings request failed{status}. Check the provider configuration."
        elif isinstance(error, LLMError):
            status = f" (HTTP {error.status})" if error.status is not None else ""
            message = f"The live provider request failed{status}. Check the provider configuration."
        else:
            message = "The critic returned an invalid reply. Try again or choose --critic local."
        print(f"Error: {message}", file=sys.stderr)
        return 1

    if args.as_json:
        payload = {
            "query": result.query,
            "draft": result.draft,
            "retrieved_ids": result.retrieved_ids,
            "critique": result.critique.model_dump(mode="json") if result.critique else None,
            "final": result.final,
            "shielded": result.shielded,
        }
        print(json.dumps(payload, indent=2))
        return 0
    if args.judge:
        if result.critique is not None:
            print(json.dumps(result.critique.model_dump(mode="json"), indent=2))
        return 0
    print(result.final)
    if args.show_critique and result.critique is not None:
        print("\n--- critique ---\n")
        print(json.dumps(result.critique.model_dump(mode="json"), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

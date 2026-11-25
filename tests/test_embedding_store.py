# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import json
from importlib import import_module
from pathlib import Path

import yaml

from absencecritic.adapters.store.embedding import (
    EmbeddingStore,
    HashEmbedder,
    OpenAIEmbedder,
    ScriptedEmbedder,
    entry_text,
)
from absencecritic.adapters.store.yaml_store import YamlStore
from eval.org_store.compare import retrieval_rates

ROOT = Path(__file__).resolve().parents[1]
ORG_DIR = ROOT / "eval" / "org_store" / "store"
PARAPHRASES = ROOT / "eval" / "org_store" / "paraphrases.yaml"


def _items() -> tuple[list[dict], list[dict]]:
    raw = yaml.safe_load(PARAPHRASES.read_text(encoding="utf-8"))
    paraphrases = list(raw["paraphrases"])
    off_topic = [{**item, "off_topic": True} for item in raw["off_topic"]]
    return paraphrases, paraphrases + off_topic


def _scripted_store() -> EmbeddingStore:
    paraphrases, _items_all = _items()
    entries = {entry.id: entry for entry in YamlStore(ORG_DIR).entries}
    groups = [
        [entry_text(entries[item["entry"]]), item["query"]] for item in paraphrases
    ]
    return EmbeddingStore(ORG_DIR, ScriptedEmbedder(groups))


def test_keyword_misses_paraphrases_and_embeddings_hit_the_right_entry():
    paraphrases, items = _items()
    keyword = retrieval_rates(YamlStore(ORG_DIR), items)
    embedded = retrieval_rates(_scripted_store(), items)
    assert keyword["right"] == 0
    assert keyword["misses"] == [item["id"] for item in paraphrases]
    assert keyword["off_topic_hits"] == 0
    assert embedded["right"] == len(paraphrases)
    assert embedded["off_topic_hits"] == 0
    assert embedded["misses"] == []


def test_keyword_still_finds_the_original_wording():
    hits = YamlStore(ORG_DIR).retrieve(
        "Should every Northwind team adopt the Atlas playbook?",
        k=3,
    )
    assert any(entry.id == "nw-atlas-launch-playbook" for entry, _score in hits)


def test_pending_and_private_notes_stay_out(tmp_path: Path):
    public = {
        "id": "public-note",
        "domain": "launches",
        "selection_process": "Only finished launches were written up.",
        "survivor_pattern": "The launch that shipped.",
        "non_survivor_evidence": "Four launches were cancelled.",
        "confidence": 0.8,
        "provenance": "fixture",
    }
    pending = {**public, "id": "pending-note", "status": "pending"}
    secret = {**public, "id": "secret-note", "non_survivor_evidence": "Hidden."}
    (tmp_path / "notes.yaml").write_text(
        yaml.safe_dump([public, pending], sort_keys=False), encoding="utf-8"
    )
    private = tmp_path / "private"
    private.mkdir()
    (private / "secret.yaml").write_text(
        yaml.safe_dump([secret], sort_keys=False), encoding="utf-8"
    )
    loaded = YamlStore(tmp_path)
    by_id = {entry.id: entry for entry in loaded.entries}
    assert "secret-note" not in by_id
    query = "Which rollout recipe should we copy?"
    groups = [[entry_text(entry), query] for entry in loaded.entries]
    hits = EmbeddingStore(tmp_path, ScriptedEmbedder(groups)).retrieve(query, k=5)
    assert [entry.id for entry, _score in hits] == ["public-note"]


def test_hash_embedder_ranks_shared_words_above_the_floor_and_drops_unrelated(tmp_path: Path):
    note = {
        "id": "shared-words",
        "domain": "knots",
        "selection_process": "Only completed knots were photographed.",
        "survivor_pattern": "A photographed bowline tied on deck.",
        "non_survivor_evidence": "Untied ropes were not photographed.",
        "confidence": 0.8,
        "provenance": "fixture",
    }
    (tmp_path / "notes.yaml").write_text(
        yaml.safe_dump([note], sort_keys=False), encoding="utf-8"
    )
    store = EmbeddingStore(tmp_path, HashEmbedder())
    same = store.retrieve(entry_text(YamlStore(tmp_path).entries[0]), k=3)
    other = store.retrieve("What is 2+2?", k=3)
    assert [entry.id for entry, _score in same] == ["shared-words"]
    assert other == []


def test_openai_embedder_posts_to_the_embeddings_endpoint():
    seen = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {"data": [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}]}
            ).encode("utf-8")

    def urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["body"] = json.loads(request.data.decode("utf-8"))
        seen["auth"] = request.get_header("Authorization")
        return _Response()

    embedder = OpenAIEmbedder(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="text-embedding-3-small",
        urlopen=urlopen,
    )
    vectors = embedder.embed_many(["alpha", "beta"])
    assert seen["url"] == "https://example.test/v1/embeddings"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"] == {"model": "text-embedding-3-small", "input": ["alpha", "beta"]}
    assert vectors == [[1.0, 0.0], [0.0, 1.0]]


def test_openai_embedder_requires_a_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    try:
        OpenAIEmbedder()
    except Exception as exc:
        assert type(exc).__name__ == "MissingEmbedKey"
    else:
        raise AssertionError("missing key should fail")


def test_cli_embedding_without_a_key_is_a_short_error(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cli_module = import_module("absencecritic.adapters.cli.main")
    monkeypatch.setattr(cli_module, "load_repo_env", lambda: None)
    code = cli_module.main(
        ["--provider", "fixture", "--retrieve", "embedding", "What is 2+2?"]
    )
    out, err = capsys.readouterr()
    assert code == 1
    assert not out
    assert "--retrieve keyword" in err
    assert "Traceback" not in err

# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

import pytest

from absencecritic.adapters.store.yaml_store import YamlStore, tokenize
from absencecritic.paths import default_store_dir

FILLER_DRAFT = (
    "They can say it is not only the same, but they often still look like they did, "
    "so it may not work for them."
)


@pytest.fixture(scope="module")
def store():
    return YamlStore(default_store_dir())


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "Should I quit my job to found a startup after reading founder success stories?",
            "college-dropout-founder-myth",
        ),
        ("Which published clinical trials show a new drug works?", "hopewell-trial-publication-bias"),
        ("What do the GitHub repositories with the most stars do right?", "github-star-survivorship"),
        ("Which benchmark leaderboard tricks should I copy for my model?", "leaderboard-overfitting"),
    ],
)
def test_on_topic_questions_find_their_entry(store, query, expected):
    assert expected in [e.id for e, _ in store.retrieve(query, k=5)]


@pytest.mark.parametrize(
    "query",
    [
        "Why are medieval castles still standing after so long?",
        "What do jackpot winners have in common?",
        "Which seeds grow best in clay soil?",
    ],
)
def test_off_topic_questions_with_filler_drafts_retrieve_nothing(store, query):
    assert store.retrieve(query, FILLER_DRAFT, k=5) == []


def test_function_words_never_count_as_overlap():
    assert tokenize(FILLER_DRAFT) == set()


def test_plurals_match_singulars():
    assert tokenize("papers companies stories") == tokenize("paper company story")
    assert tokenize("famous analysis") == {"famous", "analysis"}

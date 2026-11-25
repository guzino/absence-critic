# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from absencecritic.prompts import (
    CRITIC_DESIGN_SYSTEM,
    CRITIC_SYSTEM,
    EXPAND_SYSTEM,
    REVISE_SYSTEM,
    SCORE_DESIGN_SYSTEM,
)


def test_critic_prompt_covers_textual_plans():
    text = CRITIC_SYSTEM.lower()
    assert "plan" in text
    assert "paths not taken" in text
    assert "no write-up" in text
    assert "do not invent graphic accident" in text
    assert "do not invent" in text


def test_revise_prompt_does_not_ask_for_fictional_incidents():
    text = REVISE_SYSTEM.lower()
    assert "fictional incident" in text
    assert "paths not taken" in text


def test_clarifying_question_on_a_filtered_record_stays_a_caveat():
    from absencecritic.application.retrieve import query_names_selection

    critic = CRITIC_SYSTEM.lower()
    revise = REVISE_SYSTEM.lower()
    assert "clarifying question" in critic
    assert "at least 0.3" in critic
    assert "how-to stays in this bucket" in critic or "clarifying question on a how-to" in critic
    assert "keep that question" in revise
    for phrase in ("the literature", "published studies", "famous cases", "what survived"):
        assert phrase in critic
        assert query_names_selection(f"Ask about {phrase} here")


def test_revise_prompt_keeps_draft_steps_when_caveating():
    text = REVISE_SYSTEM.lower()
    assert "keep those steps" in text
    assert "replacing the list" in text


def test_design_prompts_forbid_invented_dead_designs():
    critic = CRITIC_DESIGN_SYSTEM.lower()
    expand = EXPAND_SYSTEM.lower()
    score = SCORE_DESIGN_SYSTEM.lower()
    assert "do not invent a lapsed patent" in critic
    assert "do not upgrade" in critic
    assert "author_prior" in critic or "author prior" in critic
    assert "hypotheses" in expand
    assert "not legal clearance" in expand
    assert "invented_dead_design" in score
    assert "rank 1" in score

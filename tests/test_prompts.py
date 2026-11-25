# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from absencecritic.prompts import CRITIC_SYSTEM, REVISE_SYSTEM


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
    critic = CRITIC_SYSTEM.lower()
    revise = REVISE_SYSTEM.lower()
    assert "clarifying question" in critic
    assert "at least 0.3" in critic
    assert "how-to stays in this bucket" in critic or "clarifying question on a how-to" in critic
    assert "keep that question" in revise


def test_revise_prompt_keeps_draft_steps_when_caveating():
    text = REVISE_SYSTEM.lower()
    assert "keep those steps" in text
    assert "replacing the list" in text

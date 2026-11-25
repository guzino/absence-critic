---
name: update-wiki
description: >-
  Update the AbsenceCritic GitHub wiki in its published layout when user-visible
  behavior, measured findings, the CLI, public terms, or the roadmap change.
  Use when editing the wiki, adding findings, changing the Wald loop or
  commands, or when Home, How it works, Try it, Words, or What comes next
  would become stale.
---

# Update the wiki

The public wiki is https://github.com/guzino/absence-critic/wiki. It is the plain-language door. Origin papers stay in `docs/`. Working plans stay in `plans/`. Do not copy either into the wiki, and do not edit `docs/` to "match" the wiki.

Design details: [design.md](design.md). The live pages are the example. Match them. Do not restyle.

## When to update

Update the wiki in the same piece of work when a reader of that page would now believe something false.

| Change | Page |
|--------|------|
| Measured finding, sample size, or what the helper did vs a sticky note | `Home.md` (short) and `Measured-results.md` (full) |
| Loop order, who may read the notebook, worry threshold, judge mode | `How-it-works.md` and the one-rule callout on `Home.md` if that rule changed |
| Install, CLI flag, practice command, live model, or where private notes go | `Try-it.md` |
| A new word a reader must know | `Words.md` |
| What is next, what already shipped, or an open issue the roadmap names | `What-comes-next.md` |

One change often touches one page. Do not rewrite the other pages to look busy.

## When to leave it

Skip the wiki for refactors, tests, encoding, CI, and prompt edits that do not change the story those pages tell. Skip it when the only new text would be a number you cannot point at in the changelog, an eval report, or `Measured-results.md`. Do not invent findings. Do not put the scoreboard or the command catalog back on the README. The README stays the short front door.

## Procedure

1. Read [design.md](design.md) and the page you will edit.
2. Clone `https://github.com/guzino/absence-critic.wiki.git` if you do not already have it. Branch is `master`. This is not a folder in the code repo.
3. Edit the page. Keep the voice: short sentences, one idea each, plain enough for a 10-year-old. Name the sample size beside any live number.
4. New picture only when the old one is now wrong. Same look as [design.md](design.md). Commit it under `images/`.
5. Commit on the wiki repo. Message says why the page changed. Plain punctuation or emoji. No curly quotes, no em dash, no ellipsis character.
6. Push `master` on the wiki repo. GitHub wikis have no pull request. Do not force-push. Do not print or embed an auth token.
7. The code change still lands as a pull request on `absence-critic`. Say in that PR, in one sentence, which wiki page you updated.
8. Confirm the page URL returns 200. If you added an image, confirm its raw URL returns 200.

Image host URL:

`https://raw.githubusercontent.com/wiki/guzino/absence-critic/images/<file>.jpg`

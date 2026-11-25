<!--
Copyright 2026 Guzino (https://github.com/guzino)
SPDX-License-Identifier: Apache-2.0
-->

<p align="center">
  <img alt="A plane that came home, holes in the wings and tail, beside the dotted outline of a plane that never returned." src="https://raw.githubusercontent.com/wiki/guzino/absence-critic/images/hero-planes.jpg" width="720">
</p>

<p align="center">
  <sub>The holes you can count are often the hits that were not deadly.</sub>
</p>

<h1 align="center">AbsenceCritic</h1>

<p align="center">
  A second reader for a chatbot.<br>
  It asks one question: <strong>are we only looking at the winners?</strong>
</p>

<p align="center">
  <a href="https://github.com/guzino/absence-critic/wiki"><strong>Read the story</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/guzino/absence-critic/wiki/How-it-works"><strong>How it works</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/guzino/absence-critic/wiki/Try-it"><strong>Try it</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/guzino/absence-critic/wiki/Measured-results"><strong>What the tests showed</strong></a>
</p>

---

## The idea

In 1943, people studied war planes that came home. The wings were full of holes. The engines were almost clean. The first idea was to armor the holes.

Abraham Wald said stop. Those diagrams show only the planes that returned. A hit in the engine often meant the plane never came back, so that hole is missing from the picture. Armor the empty spots.

A chatbot has the same problem. It learns from text that was saved: famous wins, published studies, posts that stayed online. It does not learn from the tries that failed quietly and were never written down. Ask "what works?" and it can sound sure, because it mostly read the winners.

AbsenceCritic is the helper that looks for those missing cases, then lets the writer fix the answer. On a plain fact, such as "What is 2 + 2?", the helper stays quiet.

**AbsenceCritic was designed and originated by [Guzino](https://github.com/guzino).** The name, the Wald Module, the Non-Survivor Store, and the Wald checklist are original work of that author. Wald's 1943 analysis is the historical inspiration. Using that method as a second reader for language models started in this project.

## The one rule

The writer never reads the failure notebook. Only the helper does.

The writer answers the question. The helper may look up notes about what the records left out, and it must return a report card. If the worry is high enough, the writer revises from that report card, not from the notebook. One prompt that does both jobs is not this project.

The plain-language walkthrough is on the wiki: [How it works](https://github.com/guzino/absence-critic/wiki/How-it-works).

## Try it

You need Python. Practice mode replays saved answers. No API key.

```bash
python -m pip install absencecritic
absencecritic --provider fixture "What works for launching a startup?"
```

See the same question with the helper turned off:

```bash
absencecritic --provider fixture --no-shield "What works for launching a startup?"
```

Live models, adding your own notes, and the library call are on [Try it](https://github.com/guzino/absence-critic/wiki/Try-it). This is an early release. Limits are in the [changelog](CHANGELOG.md).

## Where the rest lives

| You want | Go here |
| --- | --- |
| The story, in plain language | [Wiki](https://github.com/guzino/absence-critic/wiki) |
| What a real test showed | [Measured results](https://github.com/guzino/absence-critic/wiki/Measured-results) |
| Commands, eval, and a team's own notes | [Try it](https://github.com/guzino/absence-critic/wiki/Try-it) |
| The original design papers | [docs/](docs/00-README.md) |
| How to contribute | [CONTRIBUTING.md](CONTRIBUTING.md) |

The useful setup is the helper on answers, and the notebook pointed at failure notes your own group has, the ones a public model was never trained on.

## License and citation

[Apache License 2.0](LICENSE).

[Guzino](https://github.com/guzino). *AbsenceCritic: A Survivorship-Bias Shield for Language Models*. Version 0.1.4, 2026. https://github.com/guzino/absence-critic

```bibtex
@software{guzino_absencecritic_2026,
  author  = {Guzino},
  title   = {AbsenceCritic: A Survivorship-Bias Shield for Language Models},
  year    = {2026},
  url     = {https://github.com/guzino/absence-critic},
  version = {0.1.4},
  license = {Apache-2.0},
  note    = {Original design and conceptual origin by Guzino (https://github.com/guzino)}
}
```

A machine-readable record is in [`CITATION.cff`](CITATION.cff).

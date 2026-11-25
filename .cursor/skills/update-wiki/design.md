# Wiki design

Match this. Do not invent a second layout, a second emoji for the same idea, or a custom font. GitHub wikis do not load a stylesheet.

## Pages

| File | Role |
|------|------|
| `Home.md` | Story, one rule, a short finding |
| `How-it-works.md` | Four steps |
| `Try-it.md` | Commands, live models, library, eval entry points |
| `Measured-results.md` | Full test numbers and how to rerun them |
| `Examples.md` | Live answer excerpts |
| `Words.md` | Short dictionary |
| `What-comes-next.md` | Open jobs |
| `_Sidebar.md` | Links on every page |
| `_Footer.md` | Credit line |

Do not rename these. A new page needs a sidebar link and a link from Home, using an emoji already in the set below.

## Voice

- Short sentences. Concrete nouns. Define a new word on first use, or link `Words`.
- Straight quotes and hyphens. No curly quotes, no em dash, no ellipsis character.
- Emoji marks a section. It does not decorate every cell.
- Say what is true. A live number includes the model and that the sample is small, unless the source already says otherwise.

## Figure

Copy this shape. Width stays 880. Alt text says what the picture shows.

```html
<p align="center">
  <img alt="What the picture shows." src="https://raw.githubusercontent.com/wiki/guzino/absence-critic/images/NAME.jpg" width="880">
</p>

<p align="center">
  <sub>One or two lines. Left, then right. Or the order of the steps.</sub>
</p>
```

Under a four-part picture, add a four-column table that names the parts. Do not rely on words drawn inside the image.

## Callouts

Use GitHub alerts, not a new box style.

- `> [!IMPORTANT]` for a rule that must not break. The writer never reads the notebook.
- `> [!TIP]` for what the reader should do.
- `> [!NOTE]` for a limit. The rehearsal score is not a result.

## Emoji set

| Mark | Use only for |
|------|----------------|
| 🛡️ | The shield, the product, the fixed answer |
| ✈️ | The airplane story |
| 🤖 | A language model, or a smaller helper |
| ✍️ | The writer, a first answer |
| 🔍 | Lookup |
| 📓 | The failure notebook |
| 🔁 | How it works |
| ▶️ | Try it |
| 📖 | Words |
| 🗺️ | What comes next |
| 🤫 | Staying quiet on a plain fact |
| ✅ | Allowed, or already shipped |
| 🚫 | Not allowed |

Reuse a mark. Do not add a synonym emoji.

## Pictures

Flat vector. Warm cream background. Teal and amber. Lots of empty space. No letters, no numbers, no watermark, no fire, no blood. Wide 16:9. File name is kebab-case `.jpg` in `images/`.

Regenerate a picture only when the page's meaning changed. Keep the file name if it replaces the same figure.

## Chrome

Sidebar starts with **🛡️ AbsenceCritic**, one line on what it is, then the page links, then Code and Design papers. The claim is a second brain for language models. "Helper" and "writer" are the plain names. Do not headline it as a chatbot enhancer. The README is the short front door. Numbers and command detail stay on the wiki, not in the README.

Footer is one centered line: designed by Guzino, Wald 1943, design papers, Apache-2.0.

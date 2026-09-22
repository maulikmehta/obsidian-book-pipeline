# Examples

Two working vaults. They exist so you can see a correct book before building
your own, and so the pipeline has something to smoke-test against.

Both are public-domain text and together weigh under 6 KB. Everything a run
produces — `manuscript.qmd`, the PDFs, `Deliver/`, `skeleton.html` — is
gitignored, so the folders stay inputs.

| | `alice-novel` | `aesop-picture-book` |
|---|---|---|
| Source | *Alice's Adventures in Wonderland*, Carroll, 1865 | *The Tortoise and the Hare*, after Aesop |
| Shape | acts → chapters → scenes, nested | flat, six spreads |
| Shows | `benchmark: freytag`, act/chapter resolution | `single_pages`, `extras:`, no act structure |

## Run one

```sh
cd examples/alice-novel

python3 ../../authoring/cli.py check      # character notes + unlisted scenes
python3 ../../authoring/cli.py link       # first mentions -> character notes
python3 ../../authoring/cli.py skeleton   # structural chart
python3 ../../pipeline/build.py           # -> Deliver/<title>.pdf
```

`build.py` needs Quarto, and nothing else. Neither demo names a typeface,
so both render in Typst's default face — type is a book's design decision,
not something the pipeline should assert. To set your own, give the book its
own `_quarto.yml` and a `fonts/` folder beside `book.yml`.

## What the build target does and does not do

**`pipeline/` typesets picture books, not prose books.** Every scene's layout
lives in an `<!-- typst ... -->` comment inside the scene file, and prose
outside that comment is discarded on the way to the `.qmd`. A book drafted as
plain Markdown builds a blank PDF.

That used to happen in silence — `build.py` printed `ok` regardless. It now
warns and names the dropped scenes. These two demos carry prose and no typst
blocks, so they trip that warning on purpose: they exercise the **authoring**
half, which is format-agnostic and works fine on prose.

| | Works on plain prose? |
|---|---|
| `cli.py check` / `link` / `skeleton`, benchmarks | **yes** |
| `pipeline/build.py` | no — needs a typst block per scene |

`alice-novel/_quarto.yml` is a complete 5.5x8.5in trade-fiction setup —
binding margins, chapters opening recto, blank versos without folios,
old-style figures. It is what a novel needs, and it applies once the scenes
carry layout.

## The one thing that catches everyone

**A scene file that is not listed in `Story/Index.md` is not in the book.**
Every tool skips it silently, which reads like a broken tool rather than an
unlisted file. `cli.py check` now reports these.

Order and hierarchy come from `longform.scenes` in that file's frontmatter —
the bullet list below it is for humans. Nesting two levels deep makes a
scene; alternatively a file can declare `type: scene` itself, which is how
the flat picture book works.

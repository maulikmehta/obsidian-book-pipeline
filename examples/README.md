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

`build.py` needs Quarto. It will warn `unknown font family: charter bt` and
fall back to a default face — expected, since fonts are not redistributable
and `pipeline/fonts/` ships empty. Point `_quarto.yml` at a font you have.

## The one thing that catches everyone

**A scene file that is not listed in `Story/Index.md` is not in the book.**
Every tool skips it silently, which reads like a broken tool rather than an
unlisted file. `cli.py check` now reports these.

Order and hierarchy come from `longform.scenes` in that file's frontmatter —
the bullet list below it is for humans. Nesting two levels deep makes a
scene; alternatively a file can declare `type: scene` itself, which is how
the flat picture book works.

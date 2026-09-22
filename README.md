# obsidian-book-pipeline

Shared Quarto + Typst build for books drafted in Obsidian: one `build.py` for
an entire catalog instead of a near-identical copy per title. Renders print
PDF (with bleed, trim, cover-spread lockup) and preps the Kindle interior,
driven by a small `book.yml` per book.

Some books lean on Obsidian past plain markdown — character notes and story
skeleton linked through its graph, not just files that happen to open in it.
This pipeline picks up downstream of that: it renders whatever scene files
the vault produces, however they were organized to get there.

Built and used in production by [Swati's Journal](https://swatisjournal.com):
6 published titles, 13 live editions across Amazon.com, Amazon.in,
IngramSpark and Barnes & Noble, on owned ISBNs.

## Requirements

- [Quarto](https://quarto.org) (renders `.qmd` → Typst → PDF)
- Python 3
- ImageMagick (`magick`/`convert`) for cover cropping
- A typeface, only if you want one. The shared `_quarto.yml` names none:
  type is the book's design, so a book sets its own and keeps the faces
  in its own `fonts/`. See `pipeline/fonts/README.md` for the shared-shelf
  case.

## Layout

Each book is a folder with:

```
Book Title/
  book.yml          # this book's config (below)
  Story/*.md        # scene files, layout in <!-- typst ... --> comments
  pipeline/         # this repo's pipeline/, vendored or symlinked in
  authoring/         # this repo's authoring/, ditto
  apps/              # this repo's apps/, ditto
```

Scene files are Markdown with the Typst layout embedded in an HTML comment,
so they stay readable in a plain editor:

```markdown
<!-- typst
#place(dx: 1in, dy: 1in)[Hello]
-->
```

`print_prep.py` pulls those blocks out in file order and writes the three
Quarto inputs (`manuscript.qmd`, `cover.qmd`, `interior.qmd`); `build.py`
renders them and produces the PDFs.

### Starting a book

`init` asks three questions before it writes anything: what kind of book
this is, its trim size, and its title. The kind matters because it changes
what the build does — a **prose** book is typeset from your Markdown and
gets a `_quarto.yml` with page geometry, binding margins, chapters opening
recto and running folios; an **illustrated** book places its own layout in
`<!-- typst -->` blocks and suppresses folios, because the art carries them.

Piped or non-interactive input skips the interview, scaffolds a prose book
with defaults, and says so.

## Licence

MIT, in `LICENSE` — that covers the software.

The **AuthorKit** name and the colophon are trademarks and are not licensed
by it. Fork freely; if you ship your fork as your own, replace the mark and
the name. See [TRADEMARK.md](TRADEMARK.md).

## Examples

Two runnable vaults in [`examples/`](examples/) — a nested novel and a flat
picture book, both public-domain text, under 8 KB together. Start there:

```sh
cd examples/alice-novel && python3 ../../pipeline/build.py
```

## book.yml

```yaml
title: "Book Title"          # defaults to the folder name
targets: ["interior"]        # also available: "manuscript", "cover"
cover_prefixes: ["01-Cover"] # scene-file prefixes treated as the cover
interior_excludes: ["17-Back-Cover"]  # scenes left out of the interior
single_pages: true            # split spreads into single trim pages

# Both blocks below are OPTIONAL. Omit them and the book still builds -
# you just get no generated cover lockup and no generated front matter.
# If you DO use one, `module:` is required: it points at your own Python
# file, relative to the book folder. There is no built-in design module.
cover_lockup:
  module: ../design/cover.py   # required if cover_lockup is present
  isbn: "978-..."
  label: true
  volume: 3                    # required for the "kindle" target
interior_pages:
  module: ../design/front.py   # required if interior_pages is present
  imprint:
    isbn: "978-..."
```

### Writing a design module

`cover_lockup.module` must define:

```python
def lockup_svg(vol, label=True, isbn=None) -> str       # SVG source
def write_lockup_pdf(vol, path, label=True, isbn=None)  # writes the PDF
def render_png(svg, path)                               # SVG -> PNG
def clean_isbn(isbn) -> str | None                      # digits, or None
```

`interior_pages.module` must define `render(name, vol, cfg) -> str`, returning
Typst for each scene file named under `interior_pages.spreads`.

## Usage

```
python3 pipeline/build.py                       # build the book in cwd
python3 pipeline/build.py "Book 8" "Book 9"      # build several
```

## authoring/ — the vault-side toolkit

`pipeline/` renders a finished book; `authoring/` is what runs against the
Obsidian vault while it's still being written. Run from a book's folder (the
one holding `book.yml` and `Story/`):

```
python3 authoring/cli.py init                # interview + scaffold a vault
python3 authoring/cli.py skeleton             # render Story/ to a structural
                                               # visualization (apps/storyarc)
python3 authoring/cli.py link [--write]       # link each character's first
                                               # mention in a scene to their note
python3 authoring/cli.py check                # character notes vs act/chapter
                                               # agreement across Story/
python3 authoring/cli.py --selftest           # run the kit's own tests
```

`skeleton` compares the manuscript's actual pacing against a named structure
in `authoring/benchmarks/` (Freytag's Pyramid, or a rasa-cycle template for
non-Western dramatic shape) and renders the result via the `apps/storyarc`
visualizer. `link` is script-agnostic — which scripts it links and what
inflected tail they carry is declared per book under `book.yml`'s
`authoring.link.scripts`, so a Gujarati-only book and an English-only book
configure differently without either touching the code.

## As a Claude Code plugin

This repo doubles as the `authorkit` plugin/marketplace
(`.claude-plugin/`). Installed, it gives four skills over the same code
above — the onboarding layer the raw CLI doesn't have:

- `authorkit:book-new` — scaffold a vault (title, format, manuscript status, channels)
- `authorkit:book-build` — render print PDF + Kindle interior
- `authorkit:book-audit-manuscript` — character/act/chapter consistency
- `authorkit:book-audit-vault` — vault structure check + visual pacing snapshot

`authorkit` is meant to grow beyond this one pipeline; skill names are
scoped (`book-*`) so a future tool can add its own without colliding.

## License

MIT — see [LICENSE](LICENSE).

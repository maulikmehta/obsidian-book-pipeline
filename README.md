# quarto-book-pipeline

Shared Quarto + Typst build for illustrated books: one `build.py` for an
entire catalog instead of a near-identical copy per title. Renders print PDF
(with bleed, trim, cover-spread lockup) and preps the Kindle interior, driven
by a small `book.yml` per book.

Built and used in production by [Swati's Journal](https://swatisjournal.com)
across a dozen+ children's book titles.

## Requirements

- [Quarto](https://quarto.org) (renders `.qmd` → Typst → PDF)
- Python 3
- ImageMagick (`magick`/`convert`) for cover cropping
- Your own licensed fonts, dropped into `pipeline/fonts/` (see that folder's README)

## Layout

Each book is a folder with:

```
Book Title/
  book.yml          # this book's config (below)
  Story/*.md        # scene files, layout in <!-- typst ... --> comments
  pipeline/          # this repo, vendored or symlinked in
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

## book.yml

```yaml
title: "Book Title"          # defaults to the folder name
targets: ["interior"]        # also available: "manuscript", "cover"
cover_prefixes: ["01-Cover"] # scene-file prefixes treated as the cover
interior_excludes: ["17-Back-Cover"]  # scenes left out of the interior
single_pages: true            # split spreads into single trim pages
cover_lockup:
  isbn: "978-..."
  label: true
  volume: 3
interior_pages:
  imprint:
    isbn: "978-..."
```

## Usage

```
python3 pipeline/build.py                       # build the book in cwd
python3 pipeline/build.py "Book 8" "Book 9"      # build several
```

## License

MIT — see [LICENSE](LICENSE).

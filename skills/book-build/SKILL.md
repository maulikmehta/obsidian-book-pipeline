---
name: book-build
description: >
  Build a book's print PDF and Kindle interior from its Obsidian vault, via
  the shared Quarto+Typst pipeline. Use when the user says "build the book",
  "render the PDF", "make the interior", "authorkit build", or /book-build.
---

Run from the book's directory (must hold `book.yml` and `Story/`).

1. Confirm `book.yml` exists — if not, this isn't a book vault; suggest
   `book-new` first.
2. Run:

   ```
   python3 <path-to-authorkit>/pipeline/build.py
   ```

   Pass specific book folder names as arguments to build more than one book
   in one call (each must hold its own `book.yml`).
3. Output lands in that book's `Deliver/` folder — report what got written
   there (interior/cover/manuscript PDFs, per that book's `targets:`).
4. If the build fails on a missing font, point at `pipeline/fonts/README.md`
   — fonts aren't shipped with the pipeline (licensing), the user drops
   their own in.

---
name: book-audit-vault
description: >
  Check a book vault is set up right (book.yml valid, Story/Index.md and
  Characters/ present, fonts available for the build) and refresh its visual
  structure snapshot. Use when the user says "check my vault", "is my book
  set up right", "show my book's progress", "authorkit status", or
  /book-audit-vault.
---

Run from the book's directory.

1. Structural checklist — report each as present/missing, don't fail
   silently:
   - `book.yml` exists and parses
   - `Story/Index.md` exists (the Longform plugin's project file — scene
     order comes from it; warn if the Longform plugin itself isn't
     installed, same as `authoring/cli.py` does)
   - `Story/Characters/` exists and has at least one note
   - `<authorkit>/pipeline/fonts/` has the font(s) `_quarto.yml` names, so a
     later `book-build` won't fail partway through
2. Run:

   ```
   python3 <path-to-authorkit>/authoring/cli.py skeleton
   ```

   Renders `Strategy/creative/skeleton.html` — a visual read of the book's
   pacing (duration/intensity/key per scene) against whichever benchmark
   `book.yml` names, or the raw curve if none is set. This is the "visible
   progress from day one" artifact — point the user at the file, don't just
   say it succeeded.
3. Summarize: what's missing structurally, and a one-line read of what the
   skeleton shows (e.g. "on pace with Freytag's climax position" or "no
   benchmark set — add one under book.yml's authoring.benchmark to compare
   against").

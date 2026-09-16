---
name: book-audit-manuscript
description: >
  Check a book's manuscript for content problems: characters referenced but
  missing a note, act/chapter drift, and first mentions that could be linked
  to a character's page. Use when the user says "audit the manuscript",
  "check the story", "what's inconsistent in my book", "authorkit audit", or
  /book-audit-manuscript.
---

Run from the book's directory (must hold `book.yml` and `Story/`).

1. Run:

   ```
   python3 <path-to-authorkit>/authoring/cli.py check
   ```

   Reports characters in a scene's frontmatter with no matching note in
   `Story/Characters/`, and scenes whose act/chapter disagrees with the
   `Story/Index.md` structure. Exit code 1 means violations were found.
2. Run:

   ```
   python3 <path-to-authorkit>/authoring/cli.py link
   ```

   (no `--write`) to preview first-mention links it *would* add, without
   touching any prose. Surface the list; only re-run with `--write` if the
   user asks for the links to actually be inserted.
3. Summarize both reports together — this is a content/consistency check,
   not a structural one. For pacing/structure against a benchmark (Freytag,
   rasa-cycle), that's `authoring/cli.py skeleton`, not this skill.

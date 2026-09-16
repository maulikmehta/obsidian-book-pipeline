---
name: book-new
description: >
  Scaffold a new book vault for the authorkit pipeline: asks for the book's
  title, format, manuscript status, and target publishing channels, then
  writes book.yml and the Story/ skeleton via authoring/cli.py init. Use when
  the user says "new book", "start a book project", "set up a vault",
  "authorkit new", or /book-new.
---

Run from the directory that should become the book's vault (create it first
if it doesn't exist).

1. Ask the user for, if not already given:
   - **Title**
   - **Format**: picture book / early reader / novel / other
   - **Manuscript status**: outline only / drafting / complete
   - **Target channels**: KDP, IngramSpark, other, or none decided yet
2. Run `python3 <path-to-authorkit>/authoring/cli.py init` in the vault
   directory. This scaffolds `Story/`, `Story/Characters/`,
   `Strategy/creative/`, and a starter `book.yml`.
3. Edit the generated `book.yml`: set `title`, and add a `project:` block
   above `authoring:` recording format/status/channels as plain metadata —
   e.g.:

   ```yaml
   title: "The Book Title"
   project:
     format: picture-book
     manuscript_status: drafting
     channels: [kdp, ingramspark]
   authoring:
     ...
   ```

   Nothing in the pipeline reads `project:` yet — it's a record for the
   author and for future authorkit tools, not a build input. Don't invent
   fields beyond what was actually asked.
4. Tell the user what got created and the next commands: `book-build` once
   there's an interior to render, `book-audit-vault` any time to check the
   vault is set up right, `book-audit-manuscript` once scenes exist.

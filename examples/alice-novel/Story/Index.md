---
longform:
  scenes:
    - Act-I
    - - Chapter-1
      - - 01-The-Riverbank
        - 02-Down-The-Hole
    - Act-II
    - - Chapter-2
      - - 03-The-Hall-Of-Doors
        - 04-The-Pool-Of-Tears
---
# Alice — manuscript index

Longform reads `longform.scenes` above. Nothing else on this page is read.

**A scene file that is not listed above is not in the book.** The tools will
skip it silently, so `cli.py check` reports any unlisted file it finds.

Nesting sets the shape:

- depth 0 — front/back matter, and files whose frontmatter says `type: act`
- depth 1 — `type: chapter`
- depth 2 — scenes

Text: *Alice's Adventures in Wonderland*, Lewis Carroll, 1865. Public domain.

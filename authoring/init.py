"""Scaffold a story vault. Additive and idempotent: creates only what is
missing, never overwrites, and reports what it made.

It asks what kind of book this is, because the answer changes what the
build does. A prose book is typeset from Markdown and wants a trim size,
binding margins and running folios; an illustrated book places its own
layout in <!-- typst --> blocks and suppresses folios because the art
carries them. Guessing that wrong produces a technically-valid PDF that is
the wrong shape, which is the expensive kind of wrong.

Non-interactive (piped stdin, CI) falls back to prose defaults and says so.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "templates")

# trim -> (width_in, height_in). Bleed is added per edge at build time.
TRIMS = {
    "1": ("5 x 8in - trade paperback, novels", 5.0, 8.0),
    "2": ("5.5 x 8.5in - digest, the most common indie novel", 5.5, 8.5),
    "3": ("6 x 9in - trade, non-fiction and memoir", 6.0, 9.0),
    "4": ("8.5 x 8.5in - square, picture books", 8.5, 8.5),
    "5": ("8.5 x 11in - letter, activity and workbooks", 8.5, 11.0),
}

KINDS = {
    "1": ("prose", "Novel, novella, memoir, non-fiction - you write Markdown "
                   "and the pipeline typesets it"),
    "2": ("illustrated", "Picture book - each scene places its own art and "
                         "type in a <!-- typst --> block"),
    "3": ("activity", "Colouring, dot-marker, workbook - pages come from a "
                      "design tool, not from prose"),
}


def _ask(prompt, options, default):
    """One numbered question. Returns the chosen key."""
    print("\n  " + prompt)
    for k in sorted(options):
        print("    %s) %s" % (k, options[k][0] if isinstance(options[k], tuple)
                              else options[k]))
    try:
        got = input("  [%s] " % default).strip()
    except EOFError:
        return default
    return got if got in options else default


def interview():
    """Ask what this book is. Returns (kind, title, trim) or None if the
    session is not interactive."""
    if not sys.stdin.isatty():
        return None
    print("\n  A few questions. They set the trim size and whether the build")
    print("  typesets your prose or expects you to place layout yourself.")
    kind = KINDS[_ask("What kind of book is this?",
                      {k: (v[1],) for k, v in KINDS.items()}, "1")][0]
    default_trim = {"prose": "2", "illustrated": "4", "activity": "5"}[kind]
    tk = _ask("Trim size?", {k: (v[0],) for k, v in TRIMS.items()},
              default_trim)
    try:
        title = input("\n  Title [UNTITLED] ").strip() or "UNTITLED"
    except EOFError:
        title = "UNTITLED"
    return kind, title, TRIMS[tk]


def _book_yml(kind, title, trim):
    label, w, h = trim
    targets = '["manuscript"]' if kind == "prose" else '["interior"]'
    note = {
        "prose": "# Prose. Scenes are Markdown; the build typesets them.",
        "illustrated": "# Illustrated. Each scene places its own layout in a\n"
                       "# <!-- typst --> block; prose outside it is not set.",
        "activity": "# Activity. Pages come from a design tool. The pipeline\n"
                    "# carries metadata and front matter only.",
    }[kind]
    return """%s
title: "%s"
medium: %s
# %s
trim: [%s, %s]
targets: %s

authoring:
  intensity_field: tension
  key_field: rasa
  extras: []
  # Compare pacing against a named shape. Optional.
  # Templates live in authoring/benchmarks/ - freytag, rasa-cycle.
  # benchmark:
  #   template: freytag
  #   peak: 0.75
  link:
    scripts:
      - range: "A-Za-z"
        tail: "(?:'s)?"
""" % (note, title, kind, label, w, h, targets)


def _quarto_yml(trim):
    """A prose book needs page geometry the shared config deliberately omits."""
    _, w, h = trim
    return """# Written by `cli.py init`. Trim %s x %sin plus 0.125in bleed on
# the three outer edges. Libertinus Serif ships with Typst, so this renders
# with no fonts installed - swap it for your own licensed face.
project:
  type: default
  render:
    - manuscript.qmd

format:
  typst:
    toc: false
    number-sections: false
    mainfont: "Libertinus Serif"
    fontsize: 11pt
    include-before-body:
      - text: |
          #set page(
            width: %sin,
            height: %sin,
            margin: (top: 0.9in, bottom: 0.9in, inside: 0.875in, outside: 0.7in),
            binding: left,
          )
          #set par(leading: 0.78em, spacing: 1.1em, justify: true,
                   first-line-indent: 1.2em)

          // A blank verso carries no folio.
          #let blank = state("blank", false)
          #let open-on-recto() = {
            blank.update(true)
            pagebreak(to: "even", weak: true)
            pagebreak(to: "odd")
            blank.update(false)
          }
          #show heading.where(level: 2): it => {
            counter(heading).step()
            open-on-recto()
            v(1.2in, weak: false)
            align(center, text(size: 13pt, tracking: 0.16em)[
              #smallcaps[Chapter #counter(heading).display()]
            ])
            v(0.8em)
            align(center, text(size: 17pt, tracking: 0.06em)[#smallcaps(it.body)])
            v(2.2em, weak: false)
          }
          #set page(footer: context {
            if blank.get() { return }
            set text(size: 10pt, number-type: "old-style")
            align(center)[#counter(page).get().first()]
          })
""" % (w, h, w + 0.125, h + 0.25)


def run():
    made = []
    answers = interview()

    def mkdir(p):
        if not os.path.isdir(p):
            os.makedirs(p); made.append(p + "/")

    def copy(src, dst):
        if not os.path.exists(dst):
            shutil.copyfile(os.path.join(T, src), dst); made.append(dst)

    mkdir("Story")
    mkdir(os.path.join("Story", "Characters"))
    mkdir(os.path.join("Strategy", "creative"))
    if answers and not os.path.exists("book.yml"):
        kind, title, trim = answers
        open("book.yml", "w", encoding="utf-8").write(
            _book_yml(kind, title, trim))
        made.append("book.yml")
        if kind == "prose" and not os.path.exists("_quarto.yml"):
            open("_quarto.yml", "w", encoding="utf-8").write(_quarto_yml(trim))
            made.append("_quarto.yml")
    else:
        copy("book.yml", "book.yml")
    for f in ("emotional-ride.md", "characters.md", "environment.md"):
        copy(f, os.path.join("Strategy", "creative", f))
    copy("persona.md", os.path.join("Story", "Characters", "EXAMPLE.md"))
    if not os.path.exists(os.path.join("Story", "Index.md")):
        open(os.path.join("Story", "Index.md"), "w").write(
            "---\nlongform:\n  scenes: []\n---\n")
        made.append("Story/Index.md")

    if answers is None:
        print("\n  Not a terminal - scaffolding a prose book with defaults.")
        print("  Edit book.yml to change kind, trim or targets.")
    print()
    for m in made:
        print(f"  created {m}")
    if not made:
        print("  nothing to do")
    if not os.path.isdir(os.path.join(".obsidian", "plugins", "longform")):
        print("\n  NOTE: the Longform plugin is not installed in this vault.")
        print("  Install it in Obsidian - Story/Index.md is its project file,")
        print("  and scene order comes from it.")
    return made

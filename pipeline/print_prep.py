#!/usr/bin/env python3
"""Stitch a book's Story/*.md into the three Quarto inputs Typst renders.

Each scene file carries its layout inside an HTML comment (`<!-- typst ... -->`)
so the markdown stays readable in Obsidian. This pulls those blocks out in file
order and writes manuscript / cover / interior .qmd.

Previously this lived as 11 near-identical copies, one per book, differing only
in which scene files were held out of the interior. That difference is now
`interior_excludes` in the book's book.yml.
"""
import importlib.util
import os
import re
import sys

TYPST_BLOCK = re.compile(r'<!-- typst(.*?)-->', re.DOTALL)

DEFAULT_COVER_PREFIXES = ["01-Cover"]

# Quarto's Typst template hardcodes `numbering: "1"` on the page, which draws an
# automatic folio in the bottom margin. Every layout here sets `margin: 0in`, so
# that folio renders on the trim edge rather than inside a margin: invisible in
# a PDF viewer, but KDP's previewer flags it as text outside the margins on
# every page. The books set their own folios in the layout, so the automatic one
# is turned off here. The equivalent `page-numbering: false` in the shared
# _quarto.yml would not reach these renders - the project's `render:` list names
# manuscript.qmd only, so a `quarto render interior.qmd` picks up no project
# metadata at all.
PAGE_SETUP = "#set page(numbering: none)"

# ── bleed ──────────────────────────────────────────────────────────────
# KDP rejects a no-bleed interior whose artwork runs to the trim edge, and
# its guides sit 0.25in off every edge including the gutter - so clipping
# the art to them would open a half-inch white gap down the middle of each
# double-page illustration. Bleed is the only setting that keeps the spreads.
#
# The scene files stay authored at trim, because trim is what a designer
# measures against; the bleed is added here, on the way to the .qmd.
#
# The trick that keeps this to a handful of lines: `margin: BLEED` means a
# `#place(dx: 0in)` still lands on the *trim* corner, exactly as it did on a
# margin-0 page. Every coordinate in every scene keeps its meaning, and only
# the art that has to reach past the trim gets moved out to -BLEED.
BLEED = 0.125
TRIM = 8.5

# KDP: page width = trim + one bleed (the outer edge only - never the gutter),
# page height = trim + two (top and bottom).
SPREAD_W, PAGE_W, PAGE_H = 2 * TRIM + BLEED * 2, TRIM + BLEED, TRIM + 2 * BLEED

SPREAD_PAGE = re.compile(
    r"#set page\(width: 17in, height: 8\.5in, margin: 0in\)")
SINGLE_PAGE = re.compile(
    r"#set page\(width: 8\.5in, height: 8\.5in, margin: 0in\)")

# Artwork that covers a whole leaf or a whole spread. Anything inset - the
# 7.5in scene art at dx 0.5in - needs no change: the margin shift already
# carries it, and it never approached the trim.
FULL_ART = re.compile(
    r'#place\(dx: (0|8\.5)in, dy: 0in, image\((.*?), '
    r'width: (17|8\.5)in, height: 8\.5in, fit: "(cover|contain)"\)\)')


def _bleed_art(m):
    """Grow a full-leaf or full-spread image out to the bleed edge.

    The gutter is the one edge that never bleeds, so a right-hand leaf keeps
    dx at the fold and only grows outward; a spread grows on both sides.
    """
    dx, img, w, fit = m.group(1), m.group(2), m.group(3), m.group(4)
    dy, h = -BLEED, PAGE_H
    if w == "17":
        return ('#place(dx: %gin, dy: %gin, image(%s, width: %gin, '
                'height: %gin, fit: "%s"))' % (-BLEED, dy, img, SPREAD_W, h, fit))
    if dx == "0":                       # left leaf: bleeds left, fold on right
        return ('#place(dx: %gin, dy: %gin, image(%s, width: %gin, '
                'height: %gin, fit: "%s"))' % (-BLEED, dy, img, PAGE_W, h, fit))
    return ('#place(dx: %gin, dy: %gin, image(%s, width: %gin, '
            'height: %gin, fit: "%s"))' % (TRIM, dy, img, PAGE_W, h, fit))


# A leaf carrying a whole-page image inside a clipped block rather than a bare
# #place - the back floral, which is a wide crop held to one leaf so the two
# floral pages do not show the same crop twice. Place, block and crop all have
# to open up together: widening the block alone would leave the image short of
# it and put a white strip inside the bleed.
CLIPPED_LEAF = re.compile(
    r'#place\(\s*dx: (\d+(?:\.\d+)?)in, dy: 0in,\s*'
    r'block\(width: 8\.5in, height: 8\.5in, clip: true,\s*'
    r'align\((.*?),\s*'
    r'image\((.*?), width: (\d+(?:\.\d+)?)in, height: 8\.5in, fit: "(\w+)"\)\)\)\)',
    re.S)


def _bleed_clipped(m, bleeds_left):
    """Open a clipped leaf out to its bleed, crop and all.

    The crop grows by the same factor as the leaf, so the image keeps the
    framing it was chosen for rather than being stretched into the new box.
    """
    dx, how, img, w, fit = (m.group(1), m.group(2), m.group(3),
                            float(m.group(4)), m.group(5))
    grow = PAGE_H / TRIM
    x = float(dx) - BLEED if bleeds_left else float(dx)
    return ('#place(\n  dx: %gin, dy: %gin,\n'
            '  block(width: %gin, height: %gin, clip: true,\n'
            '    align(%s,\n      image(%s, width: %gin, height: %gin, '
            'fit: "%s"))))'
            % (x, -BLEED, PAGE_W, PAGE_H, how, img, w * grow, PAGE_H, fit))

# Every #place that positions something on the right-hand leaf of a spread.
RIGHT_HALF_DX = re.compile(r"dx: (\d+(?:\.\d+)?)in")


def _shift_right_leaf(block):
    """Move right-leaf content out by one bleed.

    On a spread whose leaves do not face each other the two trims are not
    adjacent: the left leaf bleeds off its right edge and the right leaf off
    its left, so a 0.25in strip of bleed sits between them.
    """
    def repl(m):
        dx = float(m.group(1))
        return "dx: %gin" % (dx + 2 * BLEED if dx >= TRIM else dx)
    return RIGHT_HALF_DX.sub(repl, block)


def _bleed_art_odd(m):
    """Same as _bleed_art, for a spread whose leaves do not face each other.

    Here the left leaf bleeds off its right edge and the right leaf off its
    left, the mirror of a reader's spread.
    """
    dx, img, w, fit = m.group(1), m.group(2), m.group(3), m.group(4)
    if w == "17":                       # cannot span two non-facing leaves
        return m.group(0)
    x = 0 if dx == "0" else TRIM + BLEED
    return ('#place(dx: %gin, dy: %gin, image(%s, width: %gin, '
            'height: %gin, fit: "%s"))' % (x, -BLEED, img, PAGE_W, PAGE_H, fit))


def add_bleed(block, recto, apply_bleed=True):
    """Retarget one typst block from trim to trim+bleed.

    `recto` says which leaf this block starts on, because the bleed goes on
    the outer edge and which edge that is flips leaf to leaf. Returns the
    block and how many leaves it emitted, so the caller can track parity.
    """
    if not apply_bleed:
        return block, 2 if SPREAD_PAGE.search(block) else 1
    if SPREAD_PAGE.search(block):
        if recto:
            # A spread starting on a recto is not a reader's spread at all -
            # its two leaves are the front and back of different sheets and
            # never face each other. This is how the series closes: a single
            # story page on 30 leaves the questions page on 31 and the series
            # card on 32. Both bleed off their *outer* edges, which here are
            # the two edges either side of the cut, so the page carries no
            # bleed at its outer edges and the right leaf moves out by 0.25in.
            block = SPREAD_PAGE.sub(
                "#set page(width: %gin, height: %gin, margin: (x: 0in, y: %gin))"
                % (SPREAD_W, PAGE_H, BLEED), block)
            block = _shift_right_leaf(block)
            block = CLIPPED_LEAF.sub(
                lambda m: _bleed_clipped(m, bleeds_left=True), block)
            return FULL_ART.sub(_bleed_art_odd, block), 2
        block = SPREAD_PAGE.sub(
            "#set page(width: %gin, height: %gin, margin: %gin)"
            % (SPREAD_W, PAGE_H, BLEED), block)
        block = CLIPPED_LEAF.sub(
            lambda m: _bleed_clipped(m, bleeds_left=False), block)
        return FULL_ART.sub(_bleed_art, block), 2
    if SINGLE_PAGE.search(block):
        # margin: the gutter side gets none, the outer side gets the bleed
        side = ("left: 0in, right: %gin" if recto else "right: 0in, left: %gin") % BLEED
        block = SINGLE_PAGE.sub(
            "#set page(width: %gin, height: %gin, margin: (%s, y: %gin))"
            % (PAGE_W, PAGE_H, side, BLEED), block)
        return FULL_ART.sub(_bleed_art, block), 1
    return block, 0



def load_spreads(book_dir, cfg, kindle=False):
    """Resolve book.yml's `interior_pages` into {filename: rendered typst}.

    A scene file named here is set from a shared design module instead of from
    its own `<!-- typst -->` block, so front and back matter that every volume
    shares - a copyright page, a title page, a questions page - lives in one
    place rather than in eleven copies that drift.

        interior_pages:
          module: ../Production/design-system/interior_pages.py
          volume: 2
          spreads:
            02-Copyright.md: copyright
            03-Belongs-To.md: read_aloud
            17-Questions.md: questions

    Kept generic for the same reason build.py's cover hook is: this pipeline is
    shared with books outside the series, and the module is the series' own.
    A book that says nothing about interior_pages is untouched.
    """
    spec_cfg = (cfg or {}).get("interior_pages")
    if not spec_cfg:
        return {}, None
    mod_path = os.path.normpath(os.path.join(book_dir, spec_cfg["module"]))
    if not os.path.exists(mod_path):
        raise SystemExit("  ERROR: interior_pages module not found: %s" % mod_path)

    spec = importlib.util.spec_from_file_location("interior_design", mod_path)
    design = importlib.util.module_from_spec(spec)
    sys.modules["interior_design"] = design
    spec.loader.exec_module(design)

    vol = spec_cfg["volume"]
    # `_kindle` lets a shared page drop copy that only makes sense on paper -
    # the read-aloud page tells the reader to look at the back cover, and an
    # ebook has not got one. Passed through the same dict the module already
    # reads rather than widening render()'s signature for every design module.
    spec_cfg = dict(spec_cfg, _kindle=kindle)
    spreads = {filename: design.render(name, vol, spec_cfg)
               for filename, name in spec_cfg.get("spreads", {}).items()}
    # Definitions every scene may use - a Typst `#let` at the top of the
    # document stays in scope for the blocks that follow it, so this is
    # emitted once rather than repeated in each scene that wants it.
    preamble = design.preamble() if hasattr(design, "preamble") else None
    return spreads, preamble


def scene_files(scenes_dir):
    return sorted(f for f in os.listdir(scenes_dir)
                  if f.endswith('.md') and f != 'Index.md')


def matches(filename, patterns):
    """A pattern hits either as a filename prefix or as a substring.

    Prefix covers the common '01-Cover' case; substring covers books that hold
    out every file with 'Cover' in the name regardless of position.
    """
    return any(filename.startswith(p) or p in filename for p in patterns)


def strip_wikilinks(content):
    """[[Character|મનહરે]] -> મનહરે, [[Character]] -> Character.

    Obsidian links are an authoring aid; they must never reach the page. This
    is a no-op for books that have none, so it is safe for every book.
    """
    def repl(m):
        return m.group(1).split('|')[-1]
    old = ""
    while old != content:
        old = content
        content = re.sub(r"\[\[([^\[\]]*?)\]\]", repl, content)
    return content


def process_files(files, scenes_dir, dest_path, spreads=None, preamble=None,
                  apply_bleed=True):
    spreads = spreads or {}
    # An empty target must stay empty: build.py takes a zero-byte qmd as "this
    # book has no scenes for that target" and skips it, and a preamble alone
    # would otherwise make it render a blank cover.
    out = ""
    if files:
        out = "```{=typst}\n%s\n```\n\n" % PAGE_SETUP
    if preamble and files:
        out += "```{=typst}\n%s\n```\n\n" % preamble
    # Page 1 is a recto, and every block that follows moves the count on by
    # the leaves it emits. add_bleed needs it: the bleed goes on the outer
    # edge, and which edge that is flips from leaf to leaf.
    leaf = 1
    for filename in files:
        # A shared spread replaces the file's own block entirely. The .md keeps
        # its prose so the scene still reads in Obsidian; only the layout moves.
        if filename in spreads:
            bled, leaves = add_bleed(spreads[filename], leaf % 2 == 1, apply_bleed)
            leaf += leaves
            out += "```{=typst}\n%s\n```\n\n" % bled
            continue
        with open(os.path.join(scenes_dir, filename), encoding='utf-8') as f:
            content = f.read()
        for block in TYPST_BLOCK.findall(content):
            # scene files reference ../images/ so they preview in Obsidian;
            # Quarto renders from the book root, where the path is images/
            fixed = block.strip().replace('../images/', 'images/')
            # only the extracted typst block ever reaches the .qmd (frontmatter
            # and prose outside the comment are discarded above); strip here so
            # a linked character name in dialogue never prints as raw brackets.
            fixed = strip_wikilinks(fixed)
            fixed, leaves = add_bleed(fixed, leaf % 2 == 1, apply_bleed)
            leaf += leaves
            out += "```{=typst}\n%s\n```\n\n" % fixed
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(out)
    print("  %s <- %d scene(s)" % (dest_path, len(files)))


def run(book_dir=".", cover_prefixes=None, interior_excludes=None, cfg=None,
        apply_bleed=True, kindle=False):
    scenes_dir = os.path.join(book_dir, 'Story')
    spreads, preamble = load_spreads(book_dir, cfg, kindle)
    # `or` would treat an explicit [] as unset and silently restore the
    # default, which is how a book that builds its cover elsewhere got an
    # obsolete one rendered over it.
    if cover_prefixes is None:
        cover_prefixes = DEFAULT_COVER_PREFIXES
    # default: whatever is on the cover is what the interior leaves out
    interior_excludes = (interior_excludes if interior_excludes is not None
                         else cover_prefixes)

    files = scene_files(scenes_dir)
    cover = [f for f in files if matches(f, cover_prefixes)]
    interior = [f for f in files if not matches(f, interior_excludes)]

    unused = set(spreads) - set(files)
    if unused:
        raise SystemExit("  ERROR: interior_pages names scene file(s) that do "
                         "not exist: %s" % ", ".join(sorted(unused)))

    # Only stitch what will actually be rendered. build.py builds the interior
    # alone unless a book names more targets, and writing the other two .qmd
    # anyway left dead files that looked like inputs but fed nothing.
    wanted = (cfg or {}).get("targets", ["interior"])
    for name, chosen in (("manuscript", files), ("cover", cover),
                         ("interior", interior)):
        if name in wanted:
            process_files(chosen, scenes_dir,
                          os.path.join(book_dir, name + '.qmd'),
                          spreads, preamble, apply_bleed)


if __name__ == '__main__':
    run()

#!/usr/bin/env python3
"""Shared Quarto+Typst book build.

    python3 pipeline/build.py            # build the book in cwd
    python3 pipeline/build.py "Book 8 - ..." "Book 9 - ..."

One build.py for every book in a catalog, instead of a per-book copy that
differs only in the output filename. Anything a book genuinely needs to say
for itself lives in its book.yml; everything else is shared from here,
including fonts and _quarto.yml.
"""
import importlib.util
import os
import sys
import shutil
import subprocess

import print_prep

HERE = os.path.dirname(os.path.abspath(__file__))
# The build no longer emits a CMYK companion: KDP and Ingram both take the RGB
# PDF, and the conversion only ever added a second copy of every interior.

# qmd -> Deliver filename. "{title}" is the book title from book.yml, which
# defaults to the folder name - that was the single line the 11 copies differed by.
#
# Only the interior is built unless a book asks for more. The manuscript and
# cover targets are how this pipeline used to emit a whole-book PDF and a cover
# spread; both are dead weight for this series, which composites its covers in
# Photoshop off the lockup and has no use for a second copy of the interior
# under the title. A book that still wants one says so:
#
#     targets: ["interior", "cover"]
DEFAULT_TARGETS = ["interior"]

# Kindle Create renders each page at 300 dpi of the trim size regardless of
# what it is given, so this is the resolution at which the .kpf stops being
# an upsample of a smaller page. See the kindle block in build().
KINDLE_DPI = 300

TARGETS = [
    ("manuscript.qmd", "{title}.pdf"),
    ("cover.qmd", "Cover Spread.pdf"),
    ("interior.qmd", "Interior Content.pdf"),
]


def front_cover_crop(spread_w_px, dpi=KINDLE_DPI):
    """ImageMagick crop geometry for the front trim box of a cover spread.

    The spread reads [bleed][back trim][spine][front trim][bleed]. An ebook
    cover is the front trim box alone: no bleed, and no sliver of spine. The
    offset is measured back from the right edge so it stays correct whatever
    the spine measures - that changes with the page count, and a crop written
    as "the right 50%" silently drifts into the spine when it moves.
    """
    trim = round(print_prep.TRIM * dpi)
    bleed = round(print_prep.BLEED * dpi)
    return "%dx%d+%d+%d" % (trim, trim, spread_w_px - bleed - trim, bleed)


def build_cover_lockup(book_dir, cfg):
    """Render the cover lockup from a design module named by book.yml.

    The lockup is the measured half of the cover - plaque, type, keylines,
    capsule, border - on a transparent ground, for placing over artwork. It
    is deliberately not a whole cover: the illustration and the per-volume
    palette are the two things a book decides for itself, and neither belongs
    in a shared pipeline.

    Kept generic. build.py is shared with books outside this series, so the
    module path and volume come from book.yml rather than being wired in
    here; a book that says nothing about a cover simply does not get one.

        cover_lockup:
          module: ../Production/design-system/build_template.py
          volume: 1
          label: false      # omit the back panel and draw it in Photoshop

    Returns a short status for the build log.
    """
    spec_cfg = cfg.get("cover_lockup")
    if not spec_cfg:
        return None
    mod_path = os.path.normpath(os.path.join(book_dir, spec_cfg["module"]))
    if not os.path.exists(mod_path):
        raise SystemExit("  ERROR: cover_lockup module not found: %s" % mod_path)

    spec = importlib.util.spec_from_file_location("cover_design", mod_path)
    design = importlib.util.module_from_spec(spec)
    sys.modules["cover_design"] = design
    spec.loader.exec_module(design)

    vol = spec_cfg["volume"]
    label = spec_cfg.get("label", True)
    # The barcode encodes the same ISBN the imprint page prints, so it is read
    # from there rather than written down twice; `isbn:` under cover_lockup
    # overrides for a book whose cover and interior disagree. A volume with no
    # ISBN yet keeps the placeholder patch - see clean_isbn() in the module.
    isbn = spec_cfg.get("isbn") or (cfg.get("interior_pages")
                                    or {}).get("imprint", {}).get("isbn")
    stem = "Book_%d_lockup%s" % (vol, "" if label else "_nolabel")
    deliver = os.path.join(book_dir, "Deliver")
    os.makedirs(deliver, exist_ok=True)

    import pathlib
    pdf = pathlib.Path(deliver, stem + ".pdf")
    png = pathlib.Path(deliver, stem + ".png")
    design.write_lockup_pdf(vol, pdf, label=label, isbn=isbn)
    design.render_png(design.lockup_svg(vol, label=label, isbn=isbn), png)
    code = design.clean_isbn(isbn)
    return "%s.pdf + .png (vol %d%s, %s)" % (
        stem, vol, "" if label else ", no label",
        "barcode %s" % code if code else "barcode placeholder - no ISBN")


def split_spreads(path):
    """Cut each 17in reader spread into the two 8.5in pages it prints as.

    The interiors are authored as spreads because that is how the art is
    composed - a painting that runs across the gutter has to be laid out
    across the gutter. Print wants the leaves themselves, so the deliverable
    is cut at the gutter here rather than the layout being rewritten.

    Only pages wider than they are tall are cut; the single pages the front
    and back matter already emit pass through untouched. pypdf rewrites the
    page boxes and leaves the content streams shared, so a 32-page cut of a
    100MB interior is the same 100MB and the type stays live - nothing is
    rasterised or duplicated.
    """
    import copy
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(path)
    writer = PdfWriter()
    for page in reader.pages:
        box = page.mediabox
        w, h = float(box.width), float(box.height)
        if w <= h * 1.5:
            writer.add_page(page)
            continue
        x0, y0, y1 = float(box.left), float(box.bottom), float(box.top)
        for lo, hi in ((x0, x0 + w / 2), (x0 + w / 2, x0 + w)):
            half = copy.deepcopy(page)
            half.mediabox.lower_left = (lo, y0)
            half.mediabox.upper_right = (hi, y1)
            half.cropbox = half.mediabox
            writer.add_page(half)
    with open(path, "wb") as fh:
        writer.write(fh)
    return len(reader.pages), len(writer.pages)


def load_book(book_dir):
    cfg = {}
    path = os.path.join(book_dir, "book.yml")
    if os.path.exists(path):
        import yaml
        with open(path) as fh:
            cfg = yaml.safe_load(fh) or {}
    cfg.setdefault("title", os.path.basename(os.path.abspath(book_dir)))
    return cfg


def ensure_shared(book_dir):
    """Give the book the shared _quarto.yml unless it ships its own.

    A real file in the book always wins, so a book that outgrows the shared
    layout just writes its own _quarto.yml and stops tracking this one.
    """
    local = os.path.join(book_dir, "_quarto.yml")
    shared = os.path.join(HERE, "_quarto.yml")
    if os.path.islink(local):
        if os.path.realpath(local) == os.path.realpath(shared):
            return "shared"
        os.unlink(local)
    elif os.path.exists(local):
        return "local"
    os.symlink(os.path.relpath(shared, book_dir), local)
    return "shared"


def build(book_dir):
    book_dir = os.path.abspath(book_dir)
    cfg = load_book(book_dir)
    title = cfg["title"]
    print("\n=== %s" % title)
    print("  _quarto.yml: %s" % ensure_shared(book_dir))

    print_prep.run(book_dir,
                   cover_prefixes=cfg.get("cover_prefixes"),
                   interior_excludes=cfg.get("interior_excludes"),
                   cfg=cfg)

    lockup = build_cover_lockup(book_dir, cfg)
    if lockup:
        print("  cover lockup: %s" % lockup)

    env = os.environ.copy()
    # fonts are shared; a book may still keep a local fonts/ and it wins
    paths = [os.path.join(HERE, "fonts")]
    if os.path.isdir(os.path.join(book_dir, "fonts")):
        paths.insert(0, os.path.join(book_dir, "fonts"))
    env["TYPST_FONT_PATHS"] = os.pathsep.join(paths)

    deliver = os.path.join(book_dir, "Deliver")
    os.makedirs(deliver, exist_ok=True)

    # A book may name the targets it wants; without that it gets the interior
    # alone, which is all this series ships.
    wanted = cfg.get("targets", DEFAULT_TARGETS)

    built = []
    for qmd, pattern in TARGETS:
        if qmd.rsplit(".", 1)[0] not in wanted:
            continue
        path = os.path.join(book_dir, qmd)
        # An empty qmd means the book holds no scenes for that target - a book
        # whose cover is made outside this pipeline sets cover_prefixes: [] and
        # would otherwise get an obsolete cover rendered over its real one.
        if not os.path.exists(path) or not os.path.getsize(path):
            continue
        out_name = pattern.format(title=title)
        print("  render %s -> %s" % (qmd, out_name))
        subprocess.run(["quarto", "render", qmd, "--to", "typst"],
                       check=True, cwd=book_dir, env=env)

        src = os.path.join(book_dir, qmd.replace(".qmd", ".pdf"))
        if not os.path.exists(src):
            raise SystemExit("  ERROR: quarto produced no %s" % src)

        dest = os.path.join(deliver, out_name)
        shutil.copy2(src, dest)
        # Standard for every interior: the series runs five front-matter pages
        # so the story opens on an even folio, which is what puts each half on
        # the leaf it was composed for. A book that wants the spreads intact
        # says single_pages: false.
        if cfg.get("single_pages", True) and qmd == "interior.qmd":
            was, now = split_spreads(dest)
            print("  split spreads: %d -> %d single pages" % (was, now))
        built.append(dest)
        print("  ok %s" % out_name)

    if "kindle" in wanted:
        print("\n  === Building Kindle interior (no bleed) ===")
        # A volume number names every Kindle deliverable. Defaulting it to 1
        # silently wrote Book_1_* files into whatever book was building, so a
        # book that has not said which volume it is does not get a Kindle target.
        vol = (cfg.get("cover_lockup") or cfg.get("interior_pages") or {}).get("volume")
        if vol is None:
            raise SystemExit(
                "  ERROR: the kindle target needs a volume number - set it"
                " under cover_lockup: or interior_pages: in book.yml")

        print_prep.run(book_dir,
                       cover_prefixes=cfg.get("cover_prefixes"),
                       interior_excludes=cfg.get("interior_excludes"),
                       cfg=cfg, apply_bleed=False, kindle=True)
        subprocess.run(["quarto", "render", "interior.qmd", "--to", "typst"],
                       check=True, cwd=book_dir, env=env)

        src = os.path.join(book_dir, "interior.pdf")
        kindle_pdf = os.path.join(deliver, "Kindle Content.pdf")
        shutil.copy2(src, kindle_pdf)
        if cfg.get("single_pages", True):
            split_spreads(kindle_pdf)

        lite_pdf = os.path.join(deliver, "Book_%s_Kindle_Lite.pdf" % vol)
        print("  compressing -> %s" % os.path.basename(lite_pdf))
        # Kindle Create re-renders every page at 300 dpi of the trim size no
        # matter what it is handed - a 150 dpi page comes back upsampled to the
        # same 2550px it would have been at 300, so a smaller number here buys
        # a softer book at very nearly the same delivery cost. Measured on vol 1:
        # 150 dpi -> 5.64MB .kpf, 300 dpi -> 8.36MB, both storing 2550px pages.
        #
        # DownsampleThreshold has to be spelled out: it defaults to 1.5, which
        # tells gs to leave any image less than 1.5x over target alone. The wide
        # spreads sit at 309ppi, under 1.5x of 220 and over it for 150, so the
        # output size jumped around with the dpi instead of tracking it.
        subprocess.run(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                        "-dDownsampleColorImages=true",
                        "-dColorImageResolution=%d" % KINDLE_DPI,
                        "-dColorImageDownsampleType=/Bicubic",
                        "-dColorImageDownsampleThreshold=1.0",
                        "-dAutoFilterColorImages=false",
                        "-dColorImageFilter=/DCTEncode", "-dEncodeColorImages=true",
                        # The soft masks ride along at 811ppi without these.
                        "-dDownsampleGrayImages=true",
                        "-dGrayImageResolution=%d" % KINDLE_DPI,
                        "-dGrayImageDownsampleType=/Bicubic",
                        "-dGrayImageDownsampleThreshold=1.0",
                        "-dNOPAUSE", "-dQUIET", "-dBATCH",
                        "-sOutputFile=%s" % lite_pdf, kindle_pdf], check=True)

        # The barcode spread is the live composite - it is re-exported whenever
        # an ISBN lands, so the plain spread is generally the older file. The
        # barcode sits on the back panel and the crop below takes the front, so
        # either yields the same cover: measured across vols 1-4, the two front
        # panels align at zero offset and differ by 0.3/255 mean, which is JPEG
        # recompression and nothing else. Prefer the fresher one.
        cover_pdf = next(
            (c for c in (os.path.join(deliver, "Book%s-cover-spread-barcode.pdf" % vol),
                         os.path.join(deliver, "Book%s-cover-spread.pdf" % vol))
             if os.path.exists(c)), None)
        if cover_pdf is None:
            # The lockup is a transparent overlay, not a cover, and KDP takes
            # only JPEG or TIFF with no alpha. Copying it produced a file that
            # looked like a deliverable and could never be uploaded.
            raise SystemExit(
                "  ERROR: no Book%s-cover-spread[-barcode].pdf in Deliver. The"
                " Kindle cover is cropped from the composited print spread; the"
                " lockup alone is not a cover." % vol)

        front_cover = os.path.join(deliver, "Book_%s_Kindle_Front_Cover.jpg" % vol)
        print("  extracting front cover -> %s (from %s)"
              % (os.path.basename(front_cover), os.path.basename(cover_pdf)))
        spread_w = int(subprocess.run(
            ["magick", "identify", "-density", str(KINDLE_DPI), "-format", "%w",
             cover_pdf + "[0]"],
            check=True, capture_output=True, text=True).stdout.strip())
        subprocess.run(["magick", "-density", str(KINDLE_DPI), cover_pdf + "[0]",
                        "-crop", front_cover_crop(spread_w),
                        # KDP takes JPEG or TIFF only, and rejects an alpha
                        # channel - flatten rather than carry transparency.
                        "+repage", "-background", "white", "-alpha", "remove",
                        "-colorspace", "sRGB", "-strip", "-quality", "92",
                        front_cover], check=True)

        # Restore the bled, print-worded interior.qmd so the working tree is clean
        print_prep.run(book_dir,
                       cover_prefixes=cfg.get("cover_prefixes"),
                       interior_excludes=cfg.get("interior_excludes"),
                       cfg=cfg, apply_bleed=True)

    return built


def main():
    targets = sys.argv[1:] or ["."]
    for t in targets:
        build(t)


if __name__ == "__main__":
    main()

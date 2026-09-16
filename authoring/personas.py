"""Character notes: the alias index, and the checks that keep them true.

`extras` - unnamed presences with no model sheet - comes from book.yml and
nowhere else. It used to be hardcoded in two files that had already drifted:
Petition Writer was an extra to the checker and a character to the presence
strip, so it was eligible for one of the eight principal colour slots.
"""
import os

from . import config, structure


def _dir():
    c = config.load()
    return os.path.join(config.root(), c["characters_dir"])


def index():
    """Every alias -> canonical name. Collisions are themselves an error."""
    table, dupes = {}, []
    d = _dir()
    if not os.path.isdir(d):
        return table, dupes
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md"):
            continue
        meta = structure.frontmatter(os.path.join(d, fn))
        canon = meta.get("name") or fn[:-3]
        for form in [canon] + list(meta.get("aliases") or []):
            if form in table and table[form] != canon:
                dupes.append(
                    f"{form!r} claimed by both {table[form]} and {canon}")
            table[form] = canon
    return table, dupes


def check():
    """Violations, as strings. Empty means clean."""
    c = config.load()
    extras = set(c["extras"])
    table, out = index()
    for e in structure.narrative():
        for name in (e.meta.get("characters") or []):
            if name in extras or name in table:
                continue
            out.append(f"{e.file}: {name!r} has no character note")
    for e in structure.scenes():
        if e.meta.get("act") not in (None, e.act):
            out.append(f"{e.file}: act {e.meta.get('act')} in frontmatter, "
                       f"{e.act} by position in Index.md")
        if e.meta.get("chapter") not in (None, e.chapter):
            out.append(f"{e.file}: chapter {e.meta.get('chapter')} in "
                       f"frontmatter, {e.chapter} by position in Index.md")
    return out

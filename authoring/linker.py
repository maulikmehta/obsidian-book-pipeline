"""Link each character's FIRST mention in a scene to their note.

    "...મનહરે કહ્યું"   ->   "...[[Manhar Chavda|મનહરે]] કહ્યું"

First mention only, on purpose: Obsidian counts a backlink once, so linking
every occurrence would rewrite finished prose to buy nothing.

Script-agnostic. A form is linkable if it falls in one of the ranges named in
book.yml, and each range carries the tail its script can pick up - Gujarati
case suffixes, an English possessive. Call me Sardar configures Gujarati only,
so its Latin canonical names stay unlinked exactly as before.
"""
import os
import re

from . import config, structure


def forms_for(name, aliases, scripts):
    """Linkable forms for one character, longest first."""
    out = []
    for form in [name] + list(aliases or []):
        if any(re.search(f"[{s['range']}]", form) for s in scripts):
            out.append(form)
    return sorted(set(out), key=len, reverse=True)


def tail_for(form, scripts):
    """The tail pattern belonging to the script this form is written in."""
    if not form: return ""
    for char in reversed(form):
        for s in scripts:
            if re.match(f"[{s['range']}]", char):
                return s["tail"]
    return ""


def run(write=False):
    c = config.load()
    scripts = (c["link"] or {}).get("scripts") or []
    chars_dir = os.path.join(config.root(), c["characters_dir"])
    by_canon = {}
    if os.path.isdir(chars_dir):
        for fn in sorted(os.listdir(chars_dir)):
            if fn.endswith(".md"):
                meta = structure.frontmatter(os.path.join(chars_dir, fn))
                canon = meta.get("name") or fn[:-3]
                by_canon[canon] = forms_for(canon, meta.get("aliases"), scripts)

    total = 0
    for e in structure.scenes():
        src = open(e.path, encoding="utf-8").read()
        head, fm, body = src.split("---", 2)
        new, linked = body, []
        for name in (e.meta.get("characters") or []):
            if name not in by_canon:
                continue                       # crowds and extras have no note
            if f"[[{name}|" in new:
                continue                       # already linked
            for form in by_canon[name]:
                m = re.search(re.escape(form) + tail_for(form, scripts), new)
                if not m:
                    continue
                word = m.group(0)
                new = new[:m.start()] + f"[[{name}|{word}]]" + new[m.end():]
                linked.append(f"{word} -> {name}")
                break
        if linked:
            total += len(linked)
            print(f"{e.file}: {len(linked)} linked")
            for l in linked:
                print(f"    {l}")
            if write:
                open(e.path, "w", encoding="utf-8").write(
                    head + "---" + fm + "---" + new)
    print(f"\n{total} first mentions {'linked' if write else 'would be linked'}")
    return total

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The book's structure, read from Story/Index.md — the single source of truth.

Index.md is Longform's project file. Its `scenes:` list stores nesting the way
Longform writes it: a string is an entry at the current depth, a nested list is
one level deeper (see arraysToIndentedScenes in the plugin's main.js). We use:

    depth 0 = act        depth 1 = chapter        depth 2 = scene

so dragging a scene in Obsidian's Longform pane *is* the edit that moves it in
the book. Nothing else stores order, act membership or chapter membership.

Act and chapter numbers are counted from position in the tree, never read from a
file — that is what stops them drifting. Titles come from the act/chapter notes.

    python3 structure.py        # print the tree, for eyeballing
"""
import os
import re

import yaml

from . import config


def _story():
    return os.path.join(config.root(), config.load()["story_dir"])


def _index():
    return os.path.join(_story(), "Index.md")


class Entry:
    """One node of the book: an act, a chapter, a scene, or front/back matter."""

    def __init__(self, name, depth, kind, act, chapter, meta):
        self.name = name              # note name, no .md
        self.depth = depth            # 0 act, 1 chapter, 2 scene
        self.kind = kind              # act | chapter | scene | epilogue | front | back
        self.act = act                # 1-based, None outside the acts
        self.chapter = chapter        # 1-based and book-wide, None outside
        self.meta = meta              # the note's frontmatter dict
        self.file = name + ".md"
        self.path = os.path.join(_story(), self.file)

    @property
    def title(self):
        return self.meta.get("title", self.name)

    def __repr__(self):
        return f"<{self.kind} {self.name}>"


def frontmatter(path):
    """The note's YAML frontmatter as a dict; {} if it has none."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        if f.readline().rstrip("\n") != "---":
            return {}
        block = []
        for line in f:
            if line.rstrip("\n") == "---":
                break
            block.append(line)
    return yaml.safe_load("".join(block)) or {}


def body_words(path):
    """Words of prose in a note, excluding frontmatter and wikilink markup.

    [[Manhar Chavda|મનહરે]] is one word to a reader and two to str.split(),
    so every word count in the project routes through here.
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"---\s*\n.*?\n---\s*\n", text, re.S)
    body = text[m.end():] if m else text
    body = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", body)
    body = re.sub(r"\[\[([^\]|]+)\]\]", r"\1", body)
    return len(body.split())


def _walk(node, depth=0):
    """Longform's nested arrays -> (name, depth) in reading order."""
    for item in node:
        if isinstance(item, list):
            yield from _walk(item, depth + 1)
        else:
            yield str(item), depth


def entries():
    """Every node of the book, in reading order, with act/chapter resolved."""
    scenes = (frontmatter(_index()).get("longform") or {}).get("scenes") or []
    out, act, chapter = [], 0, 0
    for name, depth in _walk(scenes):
        meta = frontmatter(os.path.join(_story(), name + ".md"))
        kind = meta.get("type") or ("scene" if depth >= 2 else "unknown")
        if kind == "act":
            act += 1
        elif kind == "chapter":
            chapter += 1
        # front/back matter sit at depth 0 beside the acts but belong to neither
        in_book = kind in ("act", "chapter", "scene")
        has_ch = kind in ("chapter", "scene")
        out.append(Entry(name, depth, kind,
                         act if in_book and act else None,
                         chapter if has_ch and chapter else None,
                         meta))
    return out


def scenes():
    """Just the scenes, in order — what the manuscript is made of."""
    return [e for e in entries() if e.kind == "scene"]


def narrative():
    """Everything that carries prose, in reading order: the scenes plus the
    epilogue. The epilogue belongs to no act, so it is not a scene — but canon
    and character rules still apply to it, and every check uses this."""
    return [e for e in entries() if e.kind in ("scene", "epilogue")]


def unlisted():
    """Scene files present in Story/ but absent from Index.md.

    A file that is not in the tree is not in the book, silently. That has
    happened once already (S-New-1), so every consumer checks.
    """
    listed = {e.file for e in entries()}
    on_disk = {f for f in os.listdir(_story())
               if f.endswith(".md") and f != "Index.md"}
    return sorted(on_disk - listed)


if __name__ == "__main__":
    for e in entries():
        print(f"{'  ' * e.depth}{e.kind:8} "
              f"a{e.act or '-'} c{e.chapter or '-'}  {e.title}")
    missing = unlisted()
    if missing:
        print("\nNOT IN THE BOOK — on disk but missing from Index.md:")
        for f in missing:
            print(f"  {f}")

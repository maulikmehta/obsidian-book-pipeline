"""Scaffold a story vault. Additive and idempotent: creates only what is
missing, never overwrites, and reports what it made."""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "templates")


def run():
    made = []

    def mkdir(p):
        if not os.path.isdir(p):
            os.makedirs(p); made.append(p + "/")

    def copy(src, dst):
        if not os.path.exists(dst):
            shutil.copyfile(os.path.join(T, src), dst); made.append(dst)

    mkdir("Story")
    mkdir(os.path.join("Story", "Characters"))
    mkdir(os.path.join("Strategy", "creative"))
    copy("book.yml", "book.yml")
    for f in ("emotional-ride.md", "characters.md", "environment.md"):
        copy(f, os.path.join("Strategy", "creative", f))
    copy("persona.md", os.path.join("Story", "Characters", "EXAMPLE.md"))
    if not os.path.exists(os.path.join("Story", "Index.md")):
        open(os.path.join("Story", "Index.md"), "w").write(
            "---\nlongform:\n  scenes: []\n---\n")
        made.append("Story/Index.md")

    for m in made:
        print(f"  created {m}")
    if not made:
        print("  nothing to do")
    if not os.path.isdir(os.path.join(".obsidian", "plugins", "longform")):
        print("\n  NOTE: the Longform plugin is not installed in this vault.")
        print("  Install it in Obsidian - Story/Index.md is its project file,")
        print("  and scene order comes from it.")
    return made

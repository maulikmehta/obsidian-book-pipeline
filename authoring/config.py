"""Per-book settings, read from book.yml in the current directory.

Root is cwd, never __file__ — the kit is shared code run against whichever
book you are standing in, exactly like pipeline/build.py.
"""
import copy
import os
import yaml
import glob
import hashlib

def _compute_kit_version():
    here = os.path.dirname(os.path.abspath(__file__))
    # Hash the toolkit and templates so the version bumps when logic or layout changes.
    # Exclude tests/ deliberately (a test change shouldn't invalidate anyone's page).
    patterns = [
        os.path.join(here, "*.py"),
        os.path.join(here, "benchmarks", "*.yml"),
        os.path.join(here, "templates", "*.html")
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    files = sorted([f for f in files if "tests" + os.sep not in f])
    
    h = hashlib.sha256()
    for f in files:
        with open(f, "rb") as fp:
            h.update(fp.read())
    return h.hexdigest()[:8]

KIT_VERSION = _compute_kit_version()

DEFAULTS = {
    "story_dir": "Story",
    "characters_dir": "Story/Characters",
    "intensity_field": "tension",
    "key_field": "rasa",
    "extras": [],
    "labels": {"unit": "scene", "duration": "words"},
    "structure": {},
    "link": {"scripts": []},
}


class BookError(Exception):
    """Raised when the current directory is not a book."""


def root():
    d = os.getcwd()
    if not os.path.exists(os.path.join(d, "book.yml")):
        raise BookError(
            f"no book.yml in {d} - run this from a book directory, "
            "the one holding Story/ and book.yml")
    return d


def load():
    with open(os.path.join(root(), "book.yml"), encoding="utf-8") as f:
        book = yaml.safe_load(f) or {}
    # deepcopy, not v.copy(): link is {"scripts": []} and a shallow copy hands
    # every caller the SAME inner list, so one append poisons DEFAULTS for the
    # rest of the process - and cli.py --selftest runs eight modules in one.
    c = copy.deepcopy(DEFAULTS)
    for k, v in (book.get("authoring") or {}).items():
        if isinstance(v, dict) and isinstance(c.get(k), dict):
            c[k].update(v)
        else:
            c[k] = v
    # Display labels default to the frontmatter field names, so a book that
    # calls its axis `rasa` gets a chart that says rasa without saying so twice.
    c["labels"]["intensity"] = c["labels"].get("intensity") or c["intensity_field"]
    c["labels"]["key"] = c["labels"].get("key") or c["key_field"]
    return c

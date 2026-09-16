import os, textwrap
from .. import personas
from .test_config import _book

BOOK = textwrap.dedent("""\
    title: X
    authoring:
      extras: [Crowd]
    """)


def _persona(d, fn, body):
    os.makedirs(os.path.join(d, "Story", "Characters"), exist_ok=True)
    open(os.path.join(d, "Story", "Characters", fn), "w").write(body)


def test_index_maps_every_alias_to_the_canonical_name():
    with _book(BOOK) as d:
        _persona(d, "Manhar Chavda.md",
                 "---\ntype: character\nname: Manhar Chavda\naliases:\n  - મનહર\n---\n")
        table, dupes = personas.index()
        assert table["મનહર"] == "Manhar Chavda"
        assert table["Manhar Chavda"] == "Manhar Chavda"
        assert dupes == []


def test_two_characters_claiming_one_alias_is_an_error():
    with _book(BOOK) as d:
        _persona(d, "A.md", "---\ntype: character\nname: A\naliases:\n  - મનહર\n---\n")
        _persona(d, "B.md", "---\ntype: character\nname: B\naliases:\n  - મનહર\n---\n")
        _, dupes = personas.index()
        assert len(dupes) == 1 and "મનહર" in dupes[0]


def test_a_declared_extra_needs_no_persona_note():
    with _book(BOOK) as d:
        _persona(d, "A.md", "---\ntype: character\nname: A\n---\n")
        open(os.path.join(d, "Story", "Index.md"), "w").write(
            "---\nlongform:\n  scenes:\n    - - - S\n---\n")
        open(os.path.join(d, "Story", "S.md"), "w").write(
            "---\ntype: scene\ncharacters:\n  - A\n  - Crowd\n---\nwords\n")
        assert personas.check() == []


def test_an_unknown_name_is_reported():
    with _book(BOOK) as d:
        _persona(d, "A.md", "---\ntype: character\nname: A\n---\n")
        open(os.path.join(d, "Story", "Index.md"), "w").write(
            "---\nlongform:\n  scenes:\n    - - - S\n---\n")
        open(os.path.join(d, "Story", "S.md"), "w").write(
            "---\ntype: scene\nact: 1\nchapter: 1\ncharacters:\n  - Nobody\n---\nwords\n")
        out = personas.check()
        assert any("Nobody" in v for v in out)


def test_act_or_chapter_drift_is_reported():
    with _book(BOOK) as d:
        _persona(d, "A.md", "---\ntype: character\nname: A\n---\n")
        open(os.path.join(d, "Story", "Index.md"), "w").write(textwrap.dedent("""\
            ---
            longform:
              scenes:
                - Act-One
                - - Chapter-One
                  - - S
            ---
            """))
        open(os.path.join(d, "Story", "Act-One.md"), "w").write("---\ntype: act\n---\n")
        open(os.path.join(d, "Story", "Chapter-One.md"), "w").write("---\ntype: chapter\n---\n")
        open(os.path.join(d, "Story", "S.md"), "w").write(
            "---\ntype: scene\nact: 2\nchapter: 2\ncharacters:\n  - A\n---\nwords\n")
        out = personas.check()
        assert any("act" in v and "S.md" in v for v in out)
        assert any("chapter" in v and "S.md" in v for v in out)


TESTS = [test_index_maps_every_alias_to_the_canonical_name,
         test_two_characters_claiming_one_alias_is_an_error,
         test_a_declared_extra_needs_no_persona_note,
         test_an_unknown_name_is_reported,
         test_act_or_chapter_drift_is_reported]

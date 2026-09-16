import os, tempfile, textwrap
from .. import structure
from .test_config import _book

INDEX = textwrap.dedent("""\
    ---
    longform:
      scenes:
        - Act-One
        - - Chapter-One
          - - Scene-1
            - Scene-2
    ---
    """)


def _scene(d, name, extra=""):
    open(os.path.join(d, "Story", name + ".md"), "w").write(
        f"---\ntype: scene\n{extra}---\nsome words here\n")


def test_act_and_chapter_come_from_tree_position():
    with _book("title: X\n") as d:
        open(os.path.join(d, "Story", "Index.md"), "w").write(INDEX)
        open(os.path.join(d, "Story", "Act-One.md"), "w").write("---\ntype: act\n---\n")
        open(os.path.join(d, "Story", "Chapter-One.md"), "w").write("---\ntype: chapter\n---\n")
        _scene(d, "Scene-1"); _scene(d, "Scene-2")
        sc = structure.scenes()
        assert [e.name for e in sc] == ["Scene-1", "Scene-2"]
        assert [e.act for e in sc] == [1, 1]
        assert [e.chapter for e in sc] == [1, 1]


def test_body_words_counts_a_wikilink_as_one_word():
    with _book("title: X\n") as d:
        p = os.path.join(d, "Story", "S.md")
        open(p, "w").write("---\ntype: scene\n---\nhe met [[Manhar Chavda|મનહરે]] today\n")
        assert structure.body_words(p) == 4


def test_unlisted_finds_a_file_absent_from_the_index():
    with _book("title: X\n") as d:
        open(os.path.join(d, "Story", "Index.md"), "w").write(INDEX)
        _scene(d, "Orphan")
        assert "Orphan.md" in structure.unlisted()


TESTS = [test_act_and_chapter_come_from_tree_position,
         test_body_words_counts_a_wikilink_as_one_word,
         test_unlisted_finds_a_file_absent_from_the_index]

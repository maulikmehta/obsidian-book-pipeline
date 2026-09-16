import os, tempfile, textwrap
from .. import config


def test_defaults_apply_when_book_yml_has_no_authoring_block():
    with _book("title: X\n") as d:
        c = config.load()
        assert c["story_dir"] == "Story"
        assert c["characters_dir"] == "Story/Characters"
        assert c["intensity_field"] == "tension"
        assert c["key_field"] == "rasa"
        assert c["extras"] == []


def test_book_values_override_defaults():
    with _book(textwrap.dedent("""\
        title: X
        authoring:
          key_field: dynamic
          extras: [Crowd]
        """)):
        c = config.load()
        assert c["key_field"] == "dynamic"
        assert c["extras"] == ["Crowd"]
        assert c["intensity_field"] == "tension"   # untouched default


def test_labels_default_to_field_names():
    with _book("title: X\nauthoring: {key_field: dynamic}\n"):
        c = config.load()
        assert c["labels"]["key"] == "dynamic"
        assert c["labels"]["intensity"] == "tension"


def test_outside_a_book_directory_fails_loudly():
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            config.load()
            assert False, "should have raised"
        except config.BookError as e:
            assert "book.yml" in str(e)
        finally:
            os.chdir(cwd)


def test_nested_mutation_does_not_poison_defaults():
    with _book("title: X\n"):
        c1 = config.load()
        c1["link"]["scripts"].append("test-script")
        assert c1["link"]["scripts"] == ["test-script"]

        c2 = config.load()
        assert c2["link"]["scripts"] == [], "second load should have fresh scripts list"


class _book:
    """A temp dir with a book.yml, made current for the duration."""
    def __init__(self, text): self.text = text
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        d = self.tmp.name
        open(os.path.join(d, "book.yml"), "w").write(self.text)
        os.makedirs(os.path.join(d, "Story"), exist_ok=True)
        open(os.path.join(d, "Story", "Index.md"), "w").write("---\n---\n")
        os.chdir(d)
        return d
    def __exit__(self, *a):
        os.chdir(self.cwd); self.tmp.cleanup()


TESTS = [test_defaults_apply_when_book_yml_has_no_authoring_block,
         test_book_values_override_defaults,
         test_labels_default_to_field_names,
         test_outside_a_book_directory_fails_loudly,
         test_nested_mutation_does_not_poison_defaults]

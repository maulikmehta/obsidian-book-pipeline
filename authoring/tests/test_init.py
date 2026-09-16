# authoring/tests/test_init.py
import os, tempfile
from .. import init


def test_init_creates_a_vault_and_is_idempotent():
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd(); os.chdir(d)
        try:
            made = init.run()
            assert os.path.exists("book.yml")
            assert os.path.isdir("Story/Characters")
            assert os.path.isdir("Strategy/creative")
            assert os.path.exists("Story/Index.md")
            assert made, "first run should report what it created"
            again = init.run()
            assert again == [], "second run must create nothing"
        finally:
            os.chdir(cwd)


def test_init_never_overwrites_an_existing_file():
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd(); os.chdir(d)
        try:
            open("book.yml", "w").write("title: Mine\n")
            init.run()
            assert open("book.yml").read() == "title: Mine\n"
        finally:
            os.chdir(cwd)


TESTS = [test_init_creates_a_vault_and_is_idempotent,
         test_init_never_overwrites_an_existing_file]

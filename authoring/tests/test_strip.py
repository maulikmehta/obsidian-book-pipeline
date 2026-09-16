import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "pipeline"))
import print_prep


def test_an_aliased_link_prints_as_its_alias():
    assert print_prep.strip_wikilinks("...[[Manhar Chavda|મનહરે]] કહ્યું") \
        == "...મનહરે કહ્યું"


def test_a_bare_link_prints_as_its_target():
    assert print_prep.strip_wikilinks("see [[Kanta Chavda]] here") \
        == "see Kanta Chavda here"


def test_text_without_links_is_untouched():
    assert print_prep.strip_wikilinks("plain prose") == "plain prose"


TESTS = [test_an_aliased_link_prints_as_its_alias,
         test_a_bare_link_prints_as_its_target,
         test_text_without_links_is_untouched]

def test_multiple_pipes_takes_the_last_segment():
    assert print_prep.strip_wikilinks("[[A|B|C]]") == "C"

def test_nested_links_are_resolved_inside_out():
    assert print_prep.strip_wikilinks("...[[Manhar Chavda|[[M|મનહરે]]]] કહ્યું") == "...મનહરે કહ્યું"

TESTS.extend([test_multiple_pipes_takes_the_last_segment, test_nested_links_are_resolved_inside_out])

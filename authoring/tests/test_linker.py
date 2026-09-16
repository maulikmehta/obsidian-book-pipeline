import re
from .. import linker

GU = {"range": "઀-૿", "tail": "[ા-્ંઃન]*"}
LA = {"range": "A-Za-z", "tail": "(?:'s)?"}


def test_only_forms_in_a_configured_script_are_linkable():
    got = linker.forms_for("Manhar Chavda", ["મનહર", "ચાવડા"], [GU])
    assert "Manhar Chavda" not in got          # Latin not configured
    assert set(got) == {"મનહર", "ચાવડા"}


def test_longest_form_wins_so_a_surname_beats_a_given_name():
    got = linker.forms_for("X", ["મનહર", "ચાવડા"], [GU])
    assert len(got[0]) >= len(got[-1])


def test_configuring_latin_makes_the_canonical_name_linkable():
    got = linker.forms_for("Shubhra", [], [LA])
    assert got == ["Shubhra"]


def test_each_script_carries_its_own_tail():
    assert linker.tail_for("મનહર", [GU, LA]) == GU["tail"]
    assert linker.tail_for("Shubhra", [GU, LA]) == LA["tail"]


def test_the_gujarati_tail_absorbs_an_inflection():
    m = re.search(re.escape("મનહર") + GU["tail"], "તેણે મનહરે કહ્યું")
    assert m.group(0) == "મનહરે"


def test_the_latin_tail_absorbs_a_possessive():
    m = re.search(re.escape("Shubhra") + LA["tail"], "it was Shubhra's letter")
    assert m.group(0) == "Shubhra's"


TESTS = [test_only_forms_in_a_configured_script_are_linkable,
         test_longest_form_wins_so_a_surname_beats_a_given_name,
         test_configuring_latin_makes_the_canonical_name_linkable,
         test_each_script_carries_its_own_tail,
         test_the_gujarati_tail_absorbs_an_inflection,
         test_the_latin_tail_absorbs_a_possessive]

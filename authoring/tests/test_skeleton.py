from .. import skeleton

C = {"work": "W", "medium": "novel", "unit": "scene", "duration_unit": "words",
     "intensity_label": "tension", "key_label": "rasa",
     "group_label": "act", "subgroup_label": "chapter",
     "rows": [dict(id=str(i), group=g, subgroup=1, cast=["A"], duration=1000,
                   intensity=t, key="k", label="", note="")
              for i, (g, t) in enumerate(
                  [(1, 2), (1, 3), (2, 5), (2, 6), (2, 7), (3, 9), (3, 4)], 1)]}


def test_contract_renders_without_a_book_directory():
    html = skeleton.render(C)
    assert "ACT" in html.upper()
    assert "1,000" in html or "1000" in html


def test_extras_do_not_take_a_principal_colour_slot():
    # Presence bars are `<line class="pb" stroke="var(--sN)">` for principals
    # and `var(--ng)` for everyone else. Assert on the bars, not the whole
    # page - the stylesheet defines --s1 whether or not anyone is assigned it.
    c = dict(C); c["extras"] = ["A"]
    bars = [l for l in skeleton.render(c).split("<line") if 'class="pb"' in l]
    assert bars, "expected presence bars for a cast member in >= 2 units"
    assert all("var(--ng)" in b for b in bars), \
        "an extra must fall through to the neutral hue"


def test_a_named_character_does_take_a_colour_slot():
    bars = [l for l in skeleton.render(C).split("<line") if 'class="pb"' in l]
    assert any("var(--s1)" in b for b in bars)


def test_findings_survive_a_contract_with_one_group():
    c = dict(C)
    c["rows"] = [dict(r, group=1) for r in C["rows"]]
    out = skeleton.findings(c)
    assert isinstance(out, list)


TESTS = [test_contract_renders_without_a_book_directory,
         test_extras_do_not_take_a_principal_colour_slot,
         test_a_named_character_does_take_a_colour_slot,
         test_findings_survive_a_contract_with_one_group]

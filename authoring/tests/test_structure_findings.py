from .. import skeleton


def _c(groups, intensities=None, expected=None):
    rows, i = [], 0
    for g, n in groups:
        for _ in range(n):
            i += 1
            rows.append(dict(id=str(i), group=g, subgroup=1, cast=[],
                             duration=1000,
                             intensity=(intensities[i-1] if intensities else 5),
                             key="k", label="", note=""))
    c = {"unit": "scene", "duration_unit": "words", "group_label": "act",
         "key_label": "rasa", "rows": rows}
    if expected:
        c["expected_proportions"] = expected
    return c


def test_proportions_are_reported_for_a_three_act_work():
    out = skeleton.structure_findings(_c([(1, 3), (2, 6), (3, 3)]))
    body = " ".join(f["desc"] for f in out)
    assert "25%" in body and "50%" in body


def test_no_warning_without_expected_proportions():
    out = skeleton.structure_findings(_c([(1, 6), (2, 3), (3, 3)]))
    assert not any(f["warn"] for f in out)


def test_drift_from_expected_proportions_warns():
    out = skeleton.structure_findings(
        _c([(1, 6), (2, 3), (3, 3)], expected=[0.25, 0.5, 0.25]))
    assert any(f["warn"] for f in out)





def test_a_single_group_produces_nothing():
    assert skeleton.structure_findings(_c([(1, 9)])) == []


def test_sharpest_turn_at_the_opening_does_not_crash():
    """The biggest jump landing on the FIRST transition left `approach`
    unbound in findings(), so any book whose sharpest turn is its opening
    move raised UnboundLocalError. Intensities 2,6,7,9 do exactly that:
    the 2->6 step is the largest and sits at index 1."""
    c = _c([(1, 2), (2, 2)], intensities=[2, 6, 7, 9])
    out = skeleton.findings(c, has_benchmark=False)
    turn = [f for f in out if f["title"] == "The sharpest turn"]
    assert turn, "the sharpest-turn finding went missing"
    assert not turn[0]["warn"], "an opening turn has nothing before it to warn about"


def test_sharpest_turn_mid_book_still_reports_its_approach():
    c = _c([(1, 2), (2, 2)], intensities=[5, 4, 9, 9])
    out = skeleton.findings(c, has_benchmark=False)
    turn = [f for f in out if f["title"] == "The sharpest turn"]
    assert turn and "before it" in turn[0]["desc"]


TESTS = [test_proportions_are_reported_for_a_three_act_work,
         test_no_warning_without_expected_proportions,
         test_drift_from_expected_proportions_warns,
         test_a_single_group_produces_nothing,
         test_sharpest_turn_at_the_opening_does_not_crash,
         test_sharpest_turn_mid_book_still_reports_its_approach]

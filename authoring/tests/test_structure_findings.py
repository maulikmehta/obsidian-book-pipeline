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


TESTS = [test_proportions_are_reported_for_a_three_act_work,
         test_no_warning_without_expected_proportions,
         test_drift_from_expected_proportions_warns,
         test_a_single_group_produces_nothing]

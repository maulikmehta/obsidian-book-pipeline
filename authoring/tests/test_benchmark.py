import os, tempfile, textwrap
from .. import config, benchmark


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


def test_load_returns_none_when_no_benchmark_block():
    with _book("title: X\n"):
        assert benchmark.load() is None


def test_load_merges_template_and_overrides():
    with _book(textwrap.dedent("""\
        title: X
        authoring:
          benchmark:
            template: freytag
            peak: 0.90
        """)):
        b = benchmark.load()
        assert b["name"] == "Freytag's Pyramid"
        assert b["peak_range"] == [0.85, 0.95]


def test_unknown_template_fails():
    with _book("title: X\nauthoring:\n  benchmark:\n    template: bogus\n"):
        try:
            benchmark.load()
            assert False, "Should raise BookError"
        except config.BookError as e:
            assert "bogus" in str(e)
            assert "freytag" in str(e)


def _contract(rows):
    return {"key_label": "rasa", "unit": "scene", "rows": rows}


def test_peak_range_rule():
    b = {"peak_range": [0.70, 0.90]}
    
    # Peak at 50%
    rows1 = [
        {"id": "1", "duration": 50, "intensity": 2},
        {"id": "1", "duration": 50, "intensity": 10},
        {"id": "1", "duration": 100, "intensity": 1}
    ]
    res1 = benchmark.compare(_contract(rows1), b)
    assert any("lands early" in r["title"] for r in res1)

    # Peak at 95%
    rows2 = [
        {"id": "1", "duration": 95, "intensity": 2},
        {"id": "1", "duration": 5, "intensity": 10},
        {"id": "1", "duration": 0, "intensity": 1}
    ]
    res2 = benchmark.compare(_contract(rows2), b)
    assert any("lands late" in r["title"] for r in res2)

    # Peak at 80%
    rows3 = [
        {"id": "1", "duration": 80, "intensity": 2},
        {"id": "1", "duration": 20, "intensity": 10}
    ]
    res3 = benchmark.compare(_contract(rows3), b)
    assert any("Peak placement" in r["title"] and not r["warn"] for r in res3)


def test_sthayi_dominance_rule():
    b = {"sthayi": "X", "sthayi_dominance": 0.50}
    rows_good = [{"id": "1", "duration": 10, "intensity": 1, "key": "X"}, {"id": "1", "duration": 10, "intensity": 1, "key": "X"}]
    res = benchmark.compare(_contract(rows_good), b)
    assert any("dominant" in r["title"] and not r["warn"] for r in res)

    rows_bad = [{"id": "1", "duration": 10, "intensity": 1, "key": "X"}, {"id": "1", "duration": 10, "intensity": 1, "key": "Y"}, {"id": "1", "duration": 10, "intensity": 1, "key": "Z"}]
    res2 = benchmark.compare(_contract(rows_bad), b)
    assert any("underweight" in r["title"] for r in res2)


def test_rasa_variety_min_rule():
    b = {"rasa_variety_min": 3}
    rows_good = [{"id": "1", "duration": 10, "intensity": 1, "key": "X"}, {"id": "1", "duration": 10, "intensity": 1, "key": "Y"}, {"id": "1", "duration": 10, "intensity": 1, "key": "Z"}]
    assert not any("Narrow palette" in r["title"] for r in benchmark.compare(_contract(rows_good), b))

    rows_bad = [{"id": "1", "duration": 10, "intensity": 1, "key": "X"}, {"id": "1", "duration": 10, "intensity": 1, "key": "X"}, {"id": "1", "duration": 10, "intensity": 1, "key": "Z"}]
    assert any("Narrow palette" in r["title"] for r in benchmark.compare(_contract(rows_bad), b))


def test_shanti_ending_rule():
    b = {"shanti_ending": True}
    rows_good = [{"id": "1", "duration": 10, "intensity": 1, "key": "શાંત"}]
    assert any("resolution" in r["title"] and not r["warn"] for r in benchmark.compare(_contract(rows_good), b) if "resolution" in r["title"])

    rows_bad = [{"id": "1", "duration": 10, "intensity": 1, "key": "X"}]
    assert any("No" in r["title"] and "resolution" in r["title"] for r in benchmark.compare(_contract(rows_bad), b))


def test_descent_required_rule():
    b = {"descent_required": True}
    
    # Descent exists
    rows_good = [{"id": "1", "duration": 10, "intensity": 10}, {"id": "1", "duration": 10, "intensity": 5}]
    assert not any("descent" in r["title"].lower() for r in benchmark.compare(_contract(rows_good), b))

    # No descent after peak
    rows_bad = [{"id": "1", "duration": 10, "intensity": 10}, {"id": "1", "duration": 10, "intensity": 10}]
    assert any("No descent after peak" in r["title"] for r in benchmark.compare(_contract(rows_bad), b))
    
    # Peak IS the final scene
    rows_end_peak = [{"id": "1", "duration": 10, "intensity": 5}, {"id": "1", "duration": 10, "intensity": 10}]
    assert any("Ends at its peak" in r["title"] for r in benchmark.compare(_contract(rows_end_peak), b))


def test_proportions_rule():
    b = {"proportions": [0.5, 0.5]}
    
    # Exact match
    rows_good = [{"id": "1", "duration": 50, "intensity": 1, "group": "1"}, {"id": "1", "duration": 50, "intensity": 1, "group": "2"}]
    assert not any("drift" in r["title"].lower() for r in benchmark.compare(_contract(rows_good), b))

    # Drift > 8%
    rows_drift = [{"id": "1", "duration": 60, "intensity": 1, "group": "1"}, {"id": "1", "duration": 40, "intensity": 1, "group": "2"}]
    assert any("drift" in r["title"].lower() for r in benchmark.compare(_contract(rows_drift), b))
    
    # Mismatch in group count (3 groups against 2 expected)
    rows_mismatch = [{"id": "1", "duration": 33, "intensity": 1, "group": "1"}, {"id": "1", "duration": 33, "intensity": 1, "group": "2"}, {"id": "1", "duration": 34, "intensity": 1, "group": "3"}]
    assert any("shape mismatch" in r["title"].lower() for r in benchmark.compare(_contract(rows_mismatch), b))


def test_min_turns_rule():
    b = {"min_turns": 1, "name": "Freytag"}
    
    # Has a turn
    rows_good = [
        {"id": "1", "duration": 10, "intensity": 1, "group": "1", "key": "A"},
        {"id": "1", "duration": 10, "intensity": 2, "group": "1", "key": "B"}
    ]
    assert not any("holds for a whole act" in r["title"] for r in benchmark.compare(_contract(rows_good), b))
    
    # Flat act (no turns)
    rows_bad = [
        {"id": "1", "duration": 10, "intensity": 1, "group": "1", "key": "A"},
        {"id": "1", "duration": 10, "intensity": 2, "group": "1", "key": "A"}
    ]
    assert any("holds for a whole act" in r["title"] for r in benchmark.compare(_contract(rows_bad), b))


TESTS = [
    test_load_returns_none_when_no_benchmark_block,
    test_load_merges_template_and_overrides,
    test_unknown_template_fails,
    test_peak_range_rule,
    test_sthayi_dominance_rule,
    test_rasa_variety_min_rule,
    test_shanti_ending_rule,
    test_descent_required_rule,
    test_proportions_rule,
    test_min_turns_rule
]

def test_peak_consistency():
    b = {"peak_range": [0.70, 0.90]}
    # Two groups on purpose: structure_findings returns nothing below two, so a
    # single-group fixture silently skips the third producer entirely.
    rows = [
        {"id": "1", "duration": 50, "intensity": 2, "key": "A", "group": 1},
        {"id": "2", "duration": 50, "intensity": 10, "key": "A", "group": 1},
        {"id": "3", "duration": 100, "intensity": 1, "key": "A", "group": 2}
    ]
    comp = benchmark.compare(_contract(rows), b)
    peak_comp = [c for c in comp if "Peak" in c["title"]][0]
    
    vit = benchmark.vitals(_contract(rows), b)
    peak_vit = [v for v in vit if v["title"] == "Climax Placement"][0]
    
    import re
    comp_pct = re.search(r"Climax at (\d+)%", peak_comp["desc"]).group(1)
    vit_pct = peak_vit["value"].replace("%", "")
    assert comp_pct == vit_pct, f"compare {comp_pct} != vitals {vit_pct}"

    # THREE producers state the climax, not two. This test originally compared
    # only compare() against vitals() - the two that already agreed - and so it
    # passed while the rendered page showed 68% in the vitals card and 59% in
    # structure_findings' "Peak sits in". Assert all three, and the shared
    # metric they are all meant to derive from.
    from authoring import skeleton, metrics
    _, _, frac = metrics.peak_position(rows)
    metric_pct = str(round(frac * 100))
    sits = [f for f in skeleton.structure_findings(_contract(rows))
            if f["title"] == "Peak sits in"]
    assert metric_pct == comp_pct, f"metrics {metric_pct} != compare {comp_pct}"
    assert sits, "fixture must produce 'Peak sits in' or this asserts nothing"
    sits_pct = re.search(r"at (\d+)%", sits[0]["desc"]).group(1)
    assert sits_pct == metric_pct, f"'Peak sits in' {sits_pct} != metrics {metric_pct}"

TESTS.append(test_peak_consistency)

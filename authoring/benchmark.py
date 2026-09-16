#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare a manuscript's actual arc against a benchmark: a canonical template
(Freytag, Rasa Cycle, …) optionally overridden by declared intent in book.yml.

    benchmark:
      template: rasa-cycle       # loads .press/authoring/benchmarks/rasa-cycle.yml
      sthayi: કરુણ               # declared dominant rasa
      peak: 0.75                 # intended climax position (0–1)
      proportions: [0.25, 0.50, 0.25]

Every field is optional. Template rules supply defaults; declared values win.
"""
import math
from authoring import metrics
import os

import yaml

from . import config


_BENCH_DIR = os.path.join(os.path.dirname(__file__), "benchmarks")


# ---- loading ---------------------------------------------------------------

def load():
    """Merge template defaults with per-book declared intent.

    Returns None if no benchmark section exists in book.yml.
    """
    c = config.load()
    decl = c.get("benchmark")
    if not decl:
        return None
    bench = {"_prov": {}}

    # load canonical template if referenced
    tname = decl.get("template")
    if tname:
        tpath = os.path.join(_BENCH_DIR, tname + ".yml")
        if not os.path.exists(tpath):
            avail = [f.replace(".yml", "") for f in os.listdir(_BENCH_DIR)
                     if f.endswith(".yml")]
            raise config.BookError(
                f"benchmark template '{tname}' not found in {_BENCH_DIR}\n"
                f"  available: {', '.join(sorted(avail))}")
        with open(tpath, encoding="utf-8") as f:
            tmpl = yaml.safe_load(f) or {}
        bench["name"] = tmpl.get("name", tname)
        bench["origin"] = tmpl.get("origin", "")
        bench["curve"] = tmpl.get("curve", [])
        rules = tmpl.get("rules") or {}
        bench.update(rules)
        for k in rules:
            bench.get("_prov", {})[k] = "canon"

    # declared intent overrides template defaults
    for key in ("peak", "sthayi", "proportions", "sthayi_dominance",
                "rasa_variety_min", "shanti_ending", "descent_required",
                "min_turns", "acts"):
        if key in decl:
            bench[key] = decl[key]
            bench.get("_prov", {})[key] = "intent"
            
    if "peak" in decl:
        bench.get("_prov", {})["peak_range"] = "intent"
    elif "peak_range" in bench:
        bench.get("_prov", {})["peak_range"] = "canon"

    # peak shorthand: scalar → range centered ±5%
    if "peak" in decl and "peak_range" not in decl:
        p = decl["peak"]
        bench["peak_range"] = [round(p - 0.05, 2), round(p + 0.05, 2)]

    return bench


# ---- comparison -------------------------------------------------------------

def _authority(bench, key):
    """Whose rule is this finding measuring against - the author's or the canon's?

    A value declared in book.yml is NOT the template's value. Crediting the
    template turns "did you mean this?" into "did you mean to depart?", which
    inverts the only distinction that tells an author whether to fix the book or
    fix the declaration.
    """
    if bench.get("_prov", {}).get(key) == "intent":
        return "your declared intent"
    return bench.get("name", "the benchmark")


def compare(contract, bench):
    """Generate diagnostic findings by comparing actuals against benchmark."""
    if not bench: return []
    rows = contract["rows"]
    if not rows: return []
    out = []
    tot = metrics.total_duration(rows)
    KL = contract.get("key_label", "rasa")
    n = len(rows)

    peak_range = bench.get("peak_range")
    if peak_range:
        peak_idx, peak_row, peak_pos = metrics.peak_position(rows)
        lo, hi = peak_range
        bname = bench.get("name", "benchmark")
        prov = bench.get("_prov", {}).get("peak_range", "canon")
        # Name the authority actually being measured against. A range derived
        # from the author's declared `peak:` is NOT the template's range, and
        # crediting the template turns "did you mean this?" into "did you mean
        # to depart?" - the distinction S5 exists to preserve.
        authority = (f"your declared peak of {round(bench['peak']*100)}%"
                     if prov == "intent" and bench.get("peak") is not None
                     else _authority(bench, "peak_range"))
        ids = [peak_row["id"]]
        leverage = max(0, lo - peak_pos, peak_pos - hi)
        if peak_pos < lo:
            out.append({"title": "Peak lands early", "desc": f"Climax at {round(peak_pos*100)}% of word count — {authority} expects {round(lo*100)}–{round(hi*100)}%. The build-up may feel rushed.", "warn": True, "leverage": leverage, "prov": prov, "ids": ids})
        elif peak_pos > hi:
            out.append({"title": "Peak lands late", "desc": f"Climax at {round(peak_pos*100)}% of word count — {authority} expects {round(lo*100)}–{round(hi*100)}%. The resolution may feel truncated.", "warn": True, "leverage": leverage, "prov": prov, "ids": ids})
        else:
            out.append({"title": "Peak placement", "desc": f"Climax at {round(peak_pos*100)}% — within the {authority} range ({round(lo*100)}–{round(hi*100)}%).", "warn": False, "leverage": leverage, "prov": prov, "ids": ids})

    sthayi = bench.get("sthayi")
    if sthayi:
        scenes = [r for r in rows if r.get("key") == sthayi]
        count = len(scenes)
        frac = count / n if n else 0
        threshold = bench.get("sthayi_dominance", 0.25)
        prov = bench.get("_prov", {}).get("sthayi", "canon")
        ids = [r["id"] for r in scenes]
        if frac < threshold:
            out.append({"title": f"{sthayi} underweight", "desc": f"{sthayi} appears in {count}/{n} scenes ({round(frac*100)}%) — below the {round(threshold*100)}% threshold for a dominant {KL}. Consider whether another {KL} is the true સ્થાયી.", "warn": True, "leverage": frac, "prov": prov, "ids": ids})
        else:
            out.append({"title": f"{sthayi} dominant", "desc": f"{sthayi} appears in {count}/{n} scenes ({round(frac*100)}%) — established as the dominant {KL}.", "warn": False, "leverage": frac, "prov": prov, "ids": ids})

    variety_min = bench.get("rasa_variety_min")
    if variety_min:
        distinct = len({r.get("key") for r in rows if r.get("key")})
        prov = bench.get("_prov", {}).get("rasa_variety_min", "canon")
        if distinct < variety_min:
            out.append({"title": "Narrow palette", "desc": f"Only {distinct} distinct {KL}(s) across {n} scenes — benchmark expects at least {variety_min}. The emotional register may feel flat.", "warn": True, "leverage": 1.0, "prov": prov, "ids": []})

    shanti = bench.get("shanti_ending")
    if shanti:
        target = "શાંત" if shanti is True else shanti
        last_key = rows[-1].get("key", "")
        is_match = last_key in ("શાંત", "Shanta", "shanta", "Śānta") if shanti is True else last_key == target
        prov = bench.get("_prov", {}).get("shanti_ending", "canon")
        ids = [rows[-1]["id"]]
        if not is_match:
            out.append({"title": f"No {target} resolution", "desc": f"The final scene's {KL} is {last_key} — {_authority(bench, 'shanti_ending')} expects resolution in {target}.", "warn": True, "leverage": rows[-1]["duration"]/tot, "prov": prov, "ids": ids})
        else:
            out.append({"title": f"{target} resolution", "desc": f"The final scene resolves in {last_key} — as {_authority(bench, 'shanti_ending')} expects.", "warn": False, "leverage": rows[-1]["duration"]/tot, "prov": prov, "ids": ids})

    if bench.get("descent_required"):
        peak_idx, peak_row, _ = metrics.peak_position(rows)
        peak_val = peak_row["intensity"]
        prov = bench.get("_prov", {}).get("descent_required", "canon")
        if peak_idx == n - 1:
            out.append({"title": "Ends at its peak", "desc": f"The highest point is the final {contract.get('unit','unit')} — there is no descent at all. {bench.get('name','The benchmark')} expects the resolution to arrive after the climax.", "warn": True, "leverage": peak_row["duration"]/tot, "prov": prov, "ids": [peak_row["id"]]})
        else:
            after = [rows[i]["intensity"] for i in range(peak_idx + 1, n)]
            if all(v >= peak_val for v in after):
                ids = [rows[i]["id"] for i in range(peak_idx + 1, n)]
                out.append({"title": "No descent after peak", "desc": f"Tension stays at or above {peak_val} after the climax — the resolution doesn't arrive emotionally.", "warn": True, "leverage": sum(rows[i]["duration"] for i in range(peak_idx+1, n))/tot, "prov": prov, "ids": ids})

    expected = bench.get("proportions")
    declared_acts = bench.get("acts")
    if expected:
        acts = {}
        for r in rows:
            g = r.get("group")
            if g is not None:
                acts.setdefault(g, 0)
                acts[g] += r["duration"]
        prov = bench.get("_prov", {}).get("proportions", "canon")
        if len(acts) != len(expected):
            out.append({"title": f"{bench.get('name','Benchmark')} shape mismatch", "desc": f"This book has {len(acts)} acts; {bench.get('name','the benchmark')} describes {declared_acts or len(expected)}. Proportions are not compared. Pick a template with the same act count, or set benchmark.proportions explicitly.", "warn": True, "leverage": 1.0, "prov": prov, "ids": []})
        else:
            actual = [acts[k] / tot for k in sorted(acts)]
            drifts = []
            max_drift = 0
            for i, (a, e) in enumerate(zip(actual, expected)):
                diff = abs(a - e)
                if diff > 0.08:
                    label = f"Act {sorted(acts.keys())[i]}"
                    drifts.append(f"{label} carries {round(a*100)}% where {_authority(bench, 'proportions')} expects {round(e*100)}% - roughly {abs(int(tot * diff)):,} words {'light' if a < e else 'heavy'}")
                    max_drift = max(max_drift, diff)
            if drifts:
                out.append({"title": "Proportion drift", "desc": "; ".join(drifts) + ".", "warn": True, "leverage": max_drift, "prov": prov, "ids": []})

    min_turns = bench.get("min_turns")
    if min_turns:
        flat = []
        flat_dur = 0
        prov = bench.get("_prov", {}).get("min_turns", "canon")
        for g in sorted({r.get("group") for r in rows if r.get("group") is not None}):
            g_rows = [r for r in rows if r.get("group") == g]
            keys = [r.get("key") for r in g_rows]
            shifts = sum(1 for i in range(1, len(keys)) if keys[i] != keys[i-1])
            if shifts < min_turns:
                flat.append((g, len(keys), shifts))
                flat_dur += sum(r["duration"] for r in g_rows)
        if flat:
            out.append({"title": f"{KL.title()} holds for a whole act", "desc": "; ".join(f"act {g} runs {n} scenes with {s} {KL} change(s)" for g, n, s in flat) + f" — {bench.get('name','the benchmark')} expects at least {min_turns} per act.", "warn": True, "leverage": flat_dur / tot, "prov": prov, "ids": []})

    curve = bench.get("curve")
    if curve and len(curve) >= 2:
        dev, max_pos, max_group = _shape_deviation(rows, curve, tot)
        if dev > 0.30: label = "significant"
        elif dev > 0.15: label = "moderate"
        else: label = "close"
        bname = bench.get("name", "benchmark")
        where = f" — strongest around {round(max_pos * 100)}% (act {max_group})" if max_group else f" — strongest around {round(max_pos * 100)}%"
        prov = bench.get("_prov", {}).get("curve", "canon")
        out.append({"title": "Shape match", "desc": f"Overall shape is a {label} match to {bname} (deviation {round(dev*100)}%){where}.", "warn": dev > 0.15, "leverage": dev, "prov": prov, "ids": []})

    return out

def template_curve_points(bench, rows, tot, lo, hi):
    curve = bench.get("curve")
    if not curve or len(curve) < 2:
        return []
    return [(p, lo + f * (hi - lo)) for p, f in curve]

def _shape_deviation(rows, curve, tot):
    """Normalised RMS distance between the actual curve and template curve.

    Samples the template at each scene's midpoint position and compares
    the normalised intensity. Returns 0.0 (identical) to ~1.0 (opposite).
    """
    n = len(rows)
    if n < 2:
        return 0.0

    intensities = [r["intensity"] for r in rows]
    lo, hi = min(intensities), max(intensities)
    span = hi - lo or 1

    # scene midpoint positions as fraction of total words
    cum = 0
    mids = []
    for r in rows:
        mid = (cum + r["duration"] / 2) / tot
        mids.append(mid)
        cum += r["duration"]

    sse = 0
    max_diff = -1
    max_pos = 0
    max_group = ""
    for i, pos in enumerate(mids):
        actual_norm = (rows[i]["intensity"] - lo) / span
        expected_norm = _lerp_curve(curve, pos)
        diff = abs(actual_norm - expected_norm)
        sse += diff ** 2
        if diff > max_diff:
            max_diff = diff
            max_pos = pos
            max_group = rows[i].get("group", "")
    return math.sqrt(sse / n), max_pos, max_group


def _lerp_curve(curve, pos):
    """Linearly interpolate the template curve at position pos (0–1)."""
    if pos <= curve[0][0]:
        return curve[0][1]
    if pos >= curve[-1][0]:
        return curve[-1][1]
    for i in range(1, len(curve)):
        if pos <= curve[i][0]:
            p0, v0 = curve[i - 1]
            p1, v1 = curve[i]
            t = (pos - p0) / (p1 - p0) if p1 != p0 else 0
            return v0 + t * (v1 - v0)
    return curve[-1][1]




def vitals(contract, bench):
    """Generate structured metric summaries for the Core Book Vitals UI."""
    if not bench: return []
    rows = contract["rows"]
    if not rows: return []
    tot = metrics.total_duration(rows)
    out = []
    
    curve = bench.get("curve")
    if curve and len(curve) >= 2:
        dev, _, _ = _shape_deviation(rows, curve, tot)
        match_pct = max(0, 100 - (dev * 100))
        status = "ok" if dev <= 0.15 else "warn" if dev <= 0.30 else "bad"
        out.append({"title": "Shape Match", "value": f"{round(match_pct)}%", "score": match_pct, "status": status, "brief": "Measures how closely the emotional pacing matches the intended structural curve.", "desc": f"Match to {bench.get('name', 'template')}"})

    peak_range = bench.get("peak_range")
    if peak_range:
        peak_idx, peak_row, peak_pos = metrics.peak_position(rows)
        lo, hi = peak_range
        status = "ok" if lo <= peak_pos <= hi else "bad"
        out.append({"title": "Climax Placement", "value": f"{round(peak_pos*100)}%", "score": peak_pos * 100, "status": status, "brief": "Checks if the highest tension point lands where the benchmark expects it.", "desc": f"Target: {round(lo*100)}–{round(hi*100)}%"})

    expected = bench.get("proportions")
    if expected:
        acts = {}
        for r in rows:
            if r.get("group") is not None:
                acts.setdefault(r["group"], 0)
                acts[r["group"]] += r["duration"]
        if len(acts) == len(expected):
            actual = [acts[k] / tot for k in sorted(acts)]
            max_drift = max(abs(a - e) for a, e in zip(actual, expected))
            drift_pct = max(0, 100 - (max_drift * 100))
            status = "ok" if max_drift <= 0.08 else "warn" if max_drift <= 0.15 else "bad"
            out.append({"title": "Act Balance", "value": f"{round(drift_pct)}%", "score": drift_pct, "status": status, "brief": "Measures if the word count is balanced across acts as intended.", "desc": f"100% = on target; largest act is {round(max_drift*100)}% off"})

    return out

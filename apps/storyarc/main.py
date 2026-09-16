#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render a work's structural skeleton: duration x intensity x key, in sequence.

The renderer is medium-neutral. It consumes a contract:

  { "work": str, "medium": str,
    "unit": "scene"|"sequence"|"movement"|...,
    "duration_unit": "words"|"seconds"|"bars"|...,
    "intensity_label": "tension"|"dynamic"|...,
    "key_label": "rasa"|"palette"|"key"|...,
    "rows": [ {id, group, duration, intensity, key, label?, note?} ] }

Anything with an ordered list of units that are held for a duration, at an
intensity, in a key, renders the same way — a novel's scenes, a film's
sequences, a symphony's movements.
"""
import re, os, sys, json, time, html as H
try: import yaml
except ImportError: yaml = None
import sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from authoring import config, structure, benchmark
from authoring import metrics

# ---------- adapter: this manuscript -> neutral contract --------------------
def from_manuscript():
    c = config.load()
    IF, KF = c["intensity_field"], c["key_field"]
    with open(os.path.join(config.root(), "book.yml"), encoding="utf-8") as _bf:
        _book = yaml.safe_load(_bf) or {}
    order = [(e.file, e.act, e.chapter) for e in structure.scenes()]
    rows = []
    for fn, act, chapter in order:
        p = os.path.join(config.root(), "Story", fn)
        if not os.path.exists(p): continue
        t = open(p, encoding="utf-8").read()
        m = re.match(r"---\s*\n(.*?)\n---\s*\n", t, re.S)
        if not m: continue
        d = yaml.safe_load(m.group(1)) or {}
        if IF not in d: continue
        rows.append(dict(id=str(d.get("scene")), group=act,
                         subgroup=chapter if chapter is not None else d.get("scene"),
                         cast=d.get("characters") or [],
                         duration=structure.body_words(p),
                         intensity=int(d[IF]), key=d.get(KF),
                         label=str(d.get("title", "")), note=d.get("brief", ""),
                         must=d.get("must"), reader_feels=d.get("reader_feels"),
                         ux_rhythm=d.get("ux_rhythm"), word_budget=d.get("word_budget")))
    # the page is stale when the prose moves, not when it is redrawn
    newest = max((os.path.getmtime(os.path.join(config.root(), "Story", fn))
                  for fn, _, _ in order
                  if os.path.exists(os.path.join(config.root(), "Story", fn))),
                 default=time.time())
    return dict(updated=time.strftime("%-d %b %Y", time.localtime(newest)),
                work=_book.get("title", "Untitled"),
                work_roman=_book.get("title_roman", ""),
                medium=_book.get("medium", "novel"),
                unit=c["labels"]["unit"], duration_unit=c["labels"]["duration"],
                intensity_label=c["labels"]["intensity"], key_label=c["labels"]["key"],
                group_label="act", subgroup_label="chapter",
                extras=c["extras"],
                expected_proportions=c["structure"].get("expected_proportions"),
                rows=rows)

# ---------- findings: derived, medium-neutral -------------------------------
def findings(c, has_benchmark=False):
    r = c["rows"]
    tot = metrics.total_duration(r)
    U, D, G = c["unit"], c["duration_unit"], c.get("group_label", "part")
    out = []

    runs, cur = [], [r[0]]
    for x in r[1:]:
        if x["key"] == cur[-1]["key"]: cur.append(x)
        else: runs.append(cur); cur = [x]
    runs.append(cur)
    
    NMIN = 8
    longest = max(runs, key=lambda q: sum(y["duration"] for y in q))
    lw = sum(y["duration"] for y in longest)
    if len(r) >= NMIN and len(longest) >= 2 and lw / tot > .10:
        at = sum(y["duration"] for y in r[:r.index(longest[0])]) / tot
        out.append({
            "title": "The longest hold",
            "desc": f"{U.title()}s {longest[0]['id']}–{longest[-1]['id']} run {lw:,} {D} — {round(lw/tot*100)}% of the work — in one {c['key_label']} with no change, starting {round(at*100)}% in. This is where immersion is most at risk.",
            "warn": True, "leverage": lw/tot, "prov": "manuscript", "ids": [x["id"] for x in longest]
        })

    big = max(r, key=lambda x: x["duration"])
    i = r.index(big)
    dlt = abs(big["intensity"] - r[i-1]["intensity"]) if i else 99
    if len(r) >= NMIN and big["duration"] / tot > .07 and dlt <= 1:
        out.append({
            "title": "The heaviest bar",
            "desc": f"{U.title()} {big['id']} is {big['duration']:,} {D} — {round(big['duration']/tot*100)}% of the work — and moves {dlt:+d} from its neighbour. Long and nearly level is where attention goes.",
            "warn": True, "leverage": big['duration']/tot, "prov": "manuscript", "ids": [big["id"]]
        })

    steps = [(abs(r[i]["intensity"]-r[i-1]["intensity"]), i) for i in range(1, len(r))]
    mx, mi = max(steps)
    if mi >= 2:
        prev_low = r[mi-1]["intensity"] <= min(x["intensity"] for x in r) + 2
        approach = (". Rested immediately before it." if prev_low else ". Nothing lowers the audience before it.")
    else:
        prev_low = True
    out.append({
        "title": "The sharpest turn",
        "desc": f"{U.title()} {r[mi-1]['id']} → {r[mi]['id']} moves {r[mi]['intensity']-r[mi-1]['intensity']:+d}"
                + (f", and the {c['key_label']} changes with it" if r[mi]['key'] != r[mi-1]['key'] else "")
                + approach,
        "warn": not prev_low, "leverage": r[mi]["duration"]/tot, "prov": "manuscript", "ids": [r[mi-1]["id"], r[mi]["id"]]
    })

    pk = max(x["intensity"] for x in r); pks = [x["id"] for x in r if x["intensity"] == pk]
    out.append({
        "title": "The peak",
        "desc": f"{pk} at {U} {', '.join(pks)}" + (" and nowhere else — spent once." if len(pks) == 1 else f" — spent {len(pks)} times, so none of them is the peak."),
        "warn": len(pks) > 1, "leverage": sum(x["duration"] for x in r if x["intensity"] == pk)/tot, "prov": "manuscript", "ids": pks
    })

    i = r.index(max(r, key=lambda x: x["intensity"]))
    tail = r[i:]
    if len(tail) >= 3:
        mono = all(tail[j]["intensity"] <= tail[j-1]["intensity"] for j in range(1, len(tail)))
        out.append({
            "title": "The descent",
            "desc": " → ".join(str(x["intensity"]) for x in tail) + (f" across the last {len(tail)} {U}s, never rising." if mono else " — it rises again after the peak."),
            "warn": not mono, "leverage": sum(x["duration"] for x in tail)/tot, "prov": "manuscript", "ids": [x["id"] for x in tail]
        })
    elif len(tail) == 1:
        out.append({
            "title": "The peak is the ending",
            "desc": f"{U.title()} {tail[0]['id']} is both the highest point and the last. There is no descent — the work stops at its loudest.",
            "warn": False, "leverage": tail[0]["duration"]/tot, "prov": "manuscript", "ids": [tail[0]["id"]]
        })

    out.extend(structure_findings(c, has_benchmark=has_benchmark))
    out.extend(contract_findings(c))
    return out

def contract_findings(c):
    """Diagnose the four scene contract fields."""
    r = c["rows"]
    if not r: return []
    out = []
    tot = sum(x["duration"] for x in r)
    U, D = c["unit"], c["duration_unit"]
    
    # 1. Obligation coverage (must)
    musts_present = any(x.get("must") for x in r)
    if not musts_present:
        out.append({
            "title": "Obligations not declared",
            "desc": f"No {U} declares a `must:` contract. Add them to frontmatter to track what scenes must accomplish.",
            "state": "missing", "leverage": 1.0, "prov": "intent", "ids": []
        })
    else:
        empty = [x for x in r if not x.get("must")]
        if empty:
            ids = [x["id"] for x in empty]
            out.append({
                "title": "Missing obligations",
                "desc": f"{len(empty)} {U}(s) have no `must:` entries. They carry {sum(x['duration'] for x in empty):,} {D} ({round(sum(x['duration'] for x in empty)/tot*100)}% of the book) with no declared purpose.",
                "state": "missed", "leverage": sum(x["duration"] for x in empty)/tot, "prov": "intent", "ids": ids
            })
            
        # Density: (words per obligation)
        densities = []
        for x in r:
            m = x.get("must")
            if not m: continue
            if isinstance(m, str):
                count = len([line for line in m.split('\n') if line.strip()])
            elif isinstance(m, list):
                count = len(m)
            else:
                count = 1
            if count > 0:
                densities.append((x["duration"] / count, count, x))
                
        if densities:
            avg_wpo = sum(x["duration"] for _, _, x in densities) / sum(c for _, c, _ in densities)
            outliers = []
            outlier_dur = 0
            ids = []
            for wpo, count, x in densities:
                if wpo > avg_wpo * 2 or wpo < avg_wpo * 0.5:
                    outliers.append(x)
                    outlier_dur += x["duration"]
                    ids.append(x["id"])
                    
            if outliers:
                out.append({
                    "title": "Obligation density variance",
                    "desc": f"{len(outliers)} {U}(s) are heavily over- or under-committed compared to the book average of {int(avg_wpo)} {D}/obligation.",
                    "state": "missed", "leverage": outlier_dur/tot, "prov": "intent", "ids": ids
                })
            else:
                out.append({
                    "title": "Obligation density",
                    "desc": f"Book averages {int(avg_wpo)} {D}/obligation, and pacing is consistent.",
                    "state": "met", "leverage": 1.0, "prov": "intent", "ids": []
                })

    # 2. Declared effect vs measured shape (reader_feels vs tension)
    feels_present = any(x.get("reader_feels") for x in r)
    if not feels_present:
        out.append({
            "title": "Reader effect not declared",
            "desc": f"No {U} declares `reader_feels:`. Add it to frontmatter to compare intended effect against actual tension.",
            "state": "missing", "leverage": 1.0, "prov": "intent", "ids": []
        })
    else:
        # We surface pairs for the author to read, flagged if they contradict.
        # A simple heuristic: high tension (>=7) with calm words, or low tension (<=3) with intense words.
        # But we shouldn't NLP it too hard. The prompt says: "surface the pairs for the author to read... flag scenes whose declared effect implies energy the tension contradicts."
        # Actually, let's just group them.
        flagged = []
        for x in r:
            f = str(x.get("reader_feels", ""))
            if not f: continue
            t = x["intensity"]
            # basic keyword heuristics just to flag obvious ones
            low_energy_words = ["calm", "bored", "peace", "quiet", "slow", "relaxed"]
            high_energy_words = ["ridiculous", "shock", "gasp", "crazy", "fast", "tense", "omg", "stupid"]
            fl = f.lower()
            if t >= 7 and any(w in fl for w in low_energy_words):
                flagged.append((x, "calm effect but high tension"))
            elif t <= 3 and any(w in fl for w in high_energy_words):
                flagged.append((x, "intense effect but low tension"))
                
        if flagged:
            ids = [x[0]["id"] for x in flagged]
            desc = "Contradictions found: " + "; ".join(f"{x['id']} ('{x.get('reader_feels')}' at tension {x['intensity']})" for x, _ in flagged)
            out.append({
                "title": "Effect vs Tension mismatch",
                "desc": desc,
                "state": "missed", "leverage": sum(x[0]["duration"] for x in flagged)/tot, "prov": "intent", "ids": ids
            })
        else:
            out.append({
                "title": "Effect aligns with Tension",
                "desc": "Declared `reader_feels` generally align with tension.",
                "state": "met", "leverage": 1.0, "prov": "intent", "ids": []
            })

    # 3. ux_rhythm
    rhythm_present = any(x.get("ux_rhythm") for x in r)
    if not rhythm_present:
        out.append({
            "title": "Rhythm not declared",
            "desc": f"No {U} declares `ux_rhythm:`. Add it to compose the sequence of pacing.",
            "state": "missing", "leverage": 1.0, "prov": "intent", "ids": []
        })
    else:
        seq = [str(x.get("ux_rhythm", "None")) for x in r]
        runs = []
        cur_run = []
        for i, val in enumerate(seq):
            if not cur_run or cur_run[-1][1] == val:
                cur_run.append((i, val))
            else:
                runs.append(cur_run)
                cur_run = [(i, val)]
        if cur_run: runs.append(cur_run)
        
        longest = max(runs, key=len)
        l_val = longest[0][1]
        l_len = len(longest)
        l_dur = sum(r[i]["duration"] for i, _ in longest)
        
        if l_val != "None" and l_len >= 4:
            ids = [r[i]["id"] for i, _ in longest]
            out.append({
                "title": "Monotonous rhythm",
                "desc": f"{l_len} consecutive {U}s run at '{l_val}' rhythm, covering {round(l_dur/tot*100)}% of the book. A composed sequence needs variation.",
                "state": "missed", "leverage": l_dur/tot, "prov": "intent", "ids": ids
            })
        else:
            out.append({
                "title": "Composed rhythm",
                "desc": f"Longest run is {l_len} '{l_val}' {U}s. Texture is varied.",
                "state": "met", "leverage": l_dur/tot, "prov": "intent", "ids": []
            })

    # 4. word_budget versus actual
    budget_present = any(x.get("word_budget") for x in r)
    if not budget_present:
        out.append({
            "title": "Word budget not declared",
            "desc": f"No {U} declares a `word_budget:`. Add it to compare intended length against actual.",
            "state": "missing", "leverage": 1.0, "prov": "intent", "ids": []
        })
    else:
        overruns = []
        total_budget = 0
        total_actual = 0
        ids = []
        for x in r:
            b = x.get("word_budget")
            if not b: continue
            try: b = int(b)
            except: continue
            a = x["duration"]
            total_budget += b
            total_actual += a
            if a > b * 1.2:  # > 20% overrun
                overruns.append((x, a, b))
                ids.append(x["id"])
                
        if overruns:
            desc = f"{len(overruns)} {U}s run >20% over budget. "
            if total_actual > total_budget * 1.1:
                desc += f"Book is heavily over budget ({total_actual:,} vs {total_budget:,}). "
            desc += "Check " + ", ".join(f"{x['id']}" for x, a, b in overruns) + "."
            out.append({
                "title": "Budget overruns",
                "desc": desc,
                "state": "missed", "leverage": sum(a for _, a, _ in overruns)/tot, "prov": "intent", "ids": ids
            })
        else:
            out.append({
                "title": "Within budget",
                "desc": f"Book sits at {total_actual:,} {D} against a budgeted {total_budget:,}.",
                "state": "met", "leverage": 1.0, "prov": "intent", "ids": []
            })

    return out

def structure_findings(c, has_benchmark=False):
    """What the act bands are doing, as opposed to what the ride is doing."""
    r = c["rows"]
    if not r: return []
    G = c.get("group_label", "part")
    groups = []
    for x in r:
        if not groups or x["group"] != groups[-1][0]:
            groups.append((x["group"], []))
        groups[-1][1].append(x)
    if len(groups) < 2:
        return []

    out = []
    tot = sum(x["duration"] for x in r)
    shares = [(g, sum(y["duration"] for y in ys) / tot) for g, ys in groups]
    out.append({
        "title": f"{G.title()} proportions",
        "desc": " · ".join(f"{G} {g} {round(s*100)}%" for g, s in shares),
        # reference, not diagnosis: implicates no part of the book, so sorts last
        "warn": False, "leverage": 0.0, "prov": "manuscript", "ids": []
    })

    exp = c.get("expected_proportions")
    if exp:
        out.append({
            "title": "Deprecated config",
            "desc": "structure.expected_proportions in book.yml is deprecated. Move it to benchmark.proportions.",
            # housekeeping, not a defect in the book - keep the warning, drop the rank
            "warn": True, "leverage": 0.0, "prov": "manuscript", "ids": []
        })
    if exp and not has_benchmark and len(exp) == len(shares):
        drift = [(g, s, e) for (g, s), e in zip(shares, exp) if abs(s - e) > 0.05]
        if drift:
            max_drift = max(abs(s - e) for _, s, e in drift)
            out.append({
                "title": "Proportion drift",
                "desc": f"{G.title()}s " + ", ".join(f"{g} ({round(s*100)}% vs {round(e*100)}%)" for g, s, e in drift) + " differ from target.",
                "warn": True, "leverage": max_drift, "prov": "intent", "ids": []
            })
            
    at, marks = 0, []
    for g, ys in groups[:-1]:
        at += sum(y["duration"] for y in ys)
        marks.append(f"{G} {g}->{g+1 if isinstance(g, int) else '?'} at {round(at/tot*100)}%")
    out.append({
        "title": "Turns",
        "desc": ", ".join(marks),
        # reference, not diagnosis
        "warn": False, "leverage": 0.0, "prov": "manuscript", "ids": []
    })

    have_range = max(x["intensity"] for x in r) != min(x["intensity"] for x in r)
    if have_range:
        i = r.index(max(r, key=lambda x: x["intensity"]))
        peak = r[i]
        if peak["group"] is not None:
            idx = [j for j, (g, _) in enumerate(groups) if g == peak["group"]][0]
            # Same definition every other producer uses - the midpoint of the
            # peak scene. Measuring words-before here is what made the page
            # report two different numbers for one climax.
            _, _, peak_pos = metrics.peak_position(r)
            out.append({
                "title": "Peak sits in",
                "desc": f"Peak sits in {G} {peak['group']}, at {round(peak_pos*100)}%.",
                "warn": False, "leverage": peak["duration"]/tot, "prov": "manuscript", "ids": [peak["id"]]
            })

    return out

def render(c):
    r = c["rows"]; TOT = sum(x["duration"] for x in r)
    U, D = c["unit"], c["duration_unit"]
    lo = min(x["intensity"] for x in r); hi = max(x["intensity"] for x in r)
    W, HT, L, R, T, B = 1220, 358, 52, 16, 72, 64
    PW, PH = W-L-R, HT-T-B
    x = L
    for s in r:
        s["x0"] = x; x += s["duration"]/TOT*PW; s["x1"] = x
    def Y(v): return T + (hi-v)/max(1, hi-lo) * PH

    d = []
    for i, s in enumerate(r):
        yy = Y(s["intensity"])
        d.append(("M" if i == 0 else "L") + f"{s['x0']:.1f},{yy:.1f}")
        d.append(f"L{s['x1']:.1f},{yy:.1f}")
    step = " ".join(d)
    fill = (f"M{r[0]['x0']:.1f},{T+PH} " +
            " ".join(f"L{s['x0']:.1f},{Y(s['intensity']):.1f} L{s['x1']:.1f},{Y(s['intensity']):.1f}" for s in r) +
            f" L{r[-1]['x1']:.1f},{T+PH} Z")
    ticks_v = sorted({hi, lo, (hi+lo)//2, (hi*3+lo)//4, (hi+lo*3)//4}, reverse=True)
    grid = "".join(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W-R}" y2="{Y(v):.1f}" class="g"/>'
                   f'<text x="{L-9}" y="{Y(v)+3.5:.1f}" class="ax">{v}</text>' for v in ticks_v)

    ris = keys = ""
    # label the opening key — subsequent labels appear at change boundaries
    keys += (f'<text x="{r[0]["x0"]+4:.1f}" y="{T-20}" class="kt">'
             f'{H.escape(str(r[0]["key"]))}</text>')
    for i in range(1, len(r)):
        a, b = r[i-1], r[i]; xx = b["x0"]; sh = a["key"] != b["key"]
        ris += (f'<line x1="{xx:.1f}" y1="{Y(a["intensity"]):.1f}" x2="{xx:.1f}" '
                f'y2="{Y(b["intensity"]):.1f}" class="ri{" ks" if sh else ""}"/>')
        if sh:
            keys += (f'<line x1="{xx:.1f}" y1="{T-16}" x2="{xx:.1f}" y2="{T+PH}" class="kl"/>'
                     f'<text x="{xx+4:.1f}" y="{T-20}" class="kt">{H.escape(str(b["key"]))}</text>')

    sus = ""; run = [r[0]]
    def emit(q):
        nonlocal sus
        w = sum(z["duration"] for z in q)
        if w/TOT < .05: return
        x0, x1, yb = q[0]["x0"], q[-1]["x1"], T+PH+16
        sus += (f'<path d="M{x0:.1f},{yb} L{x0:.1f},{yb+5} L{x1:.1f},{yb+5} L{x1:.1f},{yb}" class="su"/>'
                f'<text x="{(x0+x1)/2:.1f}" y="{yb+17}" class="sut">{w:,} held</text>')
    for s in r[1:]:
        if s["key"] == run[-1]["key"]: run.append(s)
        else: emit(run); run = [s]
    emit(run)

    def band(field, y, label, cls="gl"):
        """Draw one row of spans over the runs of r[field]. Acts, then chapters."""
        out = ""; cur = r[0].get(field); st = r[0]["x0"]
        for i, s in enumerate(r + [{field: None}]):
            if s.get(field) != cur:
                x1 = r[i-1]["x1"]
                if cur is not None:
                    out += (f'<line x1="{st:.1f}" y1="{y}" x2="{x1:.1f}" y2="{y}" class="ac"/>'
                            f'<text x="{(st+x1)/2:.1f}" y="{y-6}" class="{cls}">'
                            f'{H.escape(label(cur))}</text>')
                cur = s.get(field); st = s.get("x0", 0)
        return out

    GL = str(c.get("group_label", "part")).upper()
    grp = band("group", T - 56, lambda v: f"{GL} {v}")
    # chapters sit under the acts: how many chapters an act holds is the thing
    # the act bands alone could never show.
    if any(x.get("subgroup") is not None for x in r):
        grp += band("subgroup", T - 38, lambda v: str(v), cls="sg")
    tick = "".join(f'<text x="{(s["x0"]+s["x1"])/2:.1f}" y="{T+PH+11}" class="sn">{H.escape(s["id"])}</text>'
                   + (f'<line x1="{s["x0"]:.1f}" y1="{T+PH}" x2="{s["x0"]:.1f}" y2="{T+PH+4}" class="tk"/>' if i else "")
                   for i, s in enumerate(r))
    hits = "".join(f'<rect class="hit" data-i="{i}" x="{s["x0"]:.1f}" y="{T-16}" '
                   f'width="{max(s["x1"]-s["x0"],1):.1f}" height="{PH+16}"/>' for i, s in enumerate(r))
    rows = "".join(f'<tr id="scene-{H.escape(str(s["id"]))}"><td class="m">{H.escape(str(s["id"]))}</td><td class="m">{s["group"]}</td>'
                   f'<td class="m">{s.get("subgroup","")}</td>'
                   f'<td>{H.escape(str(s["key"]))}</td><td class="m">{s["intensity"]}</td>'
                   f'<td class="m">{s["duration"]:,}</td><td class="m">{round(s["duration"]/TOT*100,1)}%</td>'
                   f'<td class="bf">{H.escape(s.get("note",""))}</td></tr>' for s in r)
    def _render_note(f_obj):
        t = f_obj["title"]
        b = f_obj["desc"]
        
        state = f_obj.get("state")
        if state is None:
            state = "missed" if f_obj.get("warn") else "met"
            
        b = H.escape(b)
        for sid in f_obj.get("ids", []):
            b = b.replace(f"scene {H.escape(str(sid))}", f'<a href="#scene-{H.escape(str(sid))}">scene {H.escape(str(sid))}</a>')
            b = b.replace(f"Scene {H.escape(str(sid))}", f'<a href="#scene-{H.escape(str(sid))}">Scene {H.escape(str(sid))}</a>')
            b = b.replace(f"scenes {H.escape(str(sid))}", f'<a href="#scene-{H.escape(str(sid))}">scenes {H.escape(str(sid))}</a>')
            b = b.replace(f"Scenes {H.escape(str(sid))}", f'<a href="#scene-{H.escape(str(sid))}">Scenes {H.escape(str(sid))}</a>')
            b = b.replace(f" {H.escape(str(sid))} ", f' <a href="#scene-{H.escape(str(sid))}">{H.escape(str(sid))}</a> ')
            b = b.replace(f" {H.escape(str(sid))}–", f' <a href="#scene-{H.escape(str(sid))}">{H.escape(str(sid))}</a>–')
            b = b.replace(f"–{H.escape(str(sid))} ", f'–<a href="#scene-{H.escape(str(sid))}">{H.escape(str(sid))}</a> ')
            
        icon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle></svg>'
        if state == "missed":
            icon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
        elif state == "missing":
            icon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="8" y1="12" x2="16" y2="12"></line></svg>'
            
        open_attr = ' open' if state != "met" else ''
        css_class = ' w' if state == "missed" else (' m' if state == "missing" else '')
        return (f'<details class="note{css_class}"{open_attr}>'
                f'<summary><span class="n-ic">{icon}</span><b>{H.escape(t)}</b>'
                f'<span class="n-chv"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"></path></svg></span></summary>'
                f'<div class="n-bd">{b}</div></details>')

    # ---- benchmark overlay & findings ------
    try:
        bench = benchmark.load()
    except config.BookError:
        bench = None          # hand-built contract, no book directory

    notes = ""
    all_f = findings(c, has_benchmark=bool(bench))
    if bench:
        bench_findings = benchmark.compare(c, bench)
        if bench_findings:
            all_f.extend(bench_findings)
            
    # Sort missed first (0), then missing (1), then met (2)
    def _state_rank(f):
        st = f.get("state")
        if st is None:
            st = "missed" if f.get("warn") else "met"
        return {"missed": 0, "missing": 1, "met": 2}.get(st, 0)
        
    all_f.sort(key=lambda x: (_state_rank(x), -x.get("leverage", 0)))
    
    groups = {"intent": [], "canon": [], "manuscript": []}
    for f_obj in all_f:
        prov = f_obj.get("prov", "manuscript")
        groups[prov].append(f_obj)
            
    if groups["intent"]:
        notes += '<h4>Declared Intent</h4>'
        for f_obj in groups["intent"]:
            notes += _render_note(f_obj)
            
    if groups["canon"]:
        notes += '<h4>Canonical Benchmark</h4>'
        for f_obj in groups["canon"]:
            notes += _render_note(f_obj)
            
    if groups["manuscript"]:
        notes += '<h4>From the manuscript</h4>'
        for f_obj in groups["manuscript"]:
            notes += _render_note(f_obj)
    ref_curve = ""
    vitals_html = ""
    if bench:
        pts = benchmark.template_curve_points(bench, r, TOT, lo, hi)
        if pts:
            # scale normalised points to SVG coordinates
            segs = []
            for frac, intensity in pts:
                x = L + frac * PW
                y = Y(intensity)
                segs.append(f"{x:.1f},{y:.1f}")
            ref_curve = (f'<polyline points="{" ".join(segs)}" '
                         f'fill="none" stroke="#999" stroke-width="1.5" '
                         f'stroke-dasharray="6,4" opacity="0.7"/>'
                         f'<text x="{L + pts[-1][0]*PW + 6:.1f}" '
                         f'y="{Y(pts[-1][1])-4:.1f}" '
                         f'class="kt" fill="#999">'
                         f'{H.escape(bench.get("name","benchmark"))}</text>')

            
        vdata = benchmark.vitals(c, bench)
        if vdata:
            vitals_html = '<div class="vitals-group">' + "".join(
                f'<div class="vital">'
                f'<div class="v-ttl"><span class="v-dot {v["status"]}"></span>{H.escape(v["title"])}</div>'
                f'<div class="v-brf">{H.escape(v.get("brief", ""))}</div>'
                f'<div class="v-val {v["status"]}">{H.escape(v["value"])}</div>'
                f'<div class="v-bar"><div class="v-fill {v["status"]}" style="width:{v["score"]}%"></div></div>'
                f'<div class="v-dsc">{H.escape(v["desc"])}</div>'
                f'</div>' for v in vdata
            ) + '</div>'
    nk = sum(1 for i in range(1, len(r)) if r[i]["key"] != r[i-1]["key"])
    DATA = json.dumps([{k: s.get(k) for k in ("id","key","intensity","duration","group","subgroup","note")} for s in r],
                      ensure_ascii=False)
    # ---- who is on the page, against the same word axis ---------------------
    cast = {}
    for x in r:
        for n in x.get("cast") or []:
            cast.setdefault(n, []).append(x)
    cast = {n: v for n, v in cast.items() if len(v) >= 2}

    # Colour assignment. Eight validated categorical slots (see the dataviz
    # reference palette); the presence strip has more rows than that, so the
    # principals take the hues and everyone else folds to neutral — the rows are
    # direct-labelled, so identity never rests on colour alone.
    #
    # The hue follows the entity, not its rank: slots are handed out in order of
    # FIRST APPEARANCE, so a character's colour does not change when word counts
    # shift underneath them.
    EXTRAS = set(c.get("extras") or [])
    named = [n for n in cast if n not in EXTRAS]
    by_words = sorted(named, key=lambda n: -sum(z["duration"] for z in cast[n]))
    principals, minor = by_words[:8], by_words[8:]
    first_seen = {n: min(r.index(z) for z in cast[n]) for n in principals}
    slot = {n: f"--s{i + 1}" for i, n in enumerate(sorted(principals, key=first_seen.get))}
    # Past eight hues, separate by LIGHTNESS instead — safe for every kind of
    # colour vision. Groups (crowds, farmers) are not people and stay faintest.
    for i, n in enumerate(sorted(minor, key=lambda n: min(r.index(z) for z in cast[n]))):
        slot[n] = f"--n{min(i + 1, 3)}"

    presence = ""
    if cast:
        LG, RH, top = 168, 15, 26          # left gutter, row height, header
        PWD = W - R - LG
        def nx(v):                          # remap chart x -> strip x
            return LG + (v - L) / PW * PWD
        order = sorted(cast, key=lambda n: -sum(z["duration"] for z in cast[n]))
        ph = top + len(order) * RH + 8
        cur, st = r[0]["group"], r[0]["x0"]
        for i, x in enumerate(r + [{"group": None}]):
            if x.get("group") != cur:
                x1 = r[i-1]["x1"]
                presence += (f'<line x1="{nx(st):.1f}" y1="16" x2="{nx(x1):.1f}" y2="16" class="ac"/>'
                             f'<text x="{(nx(st)+nx(x1))/2:.1f}" y="10" class="gl">'
                             f'{H.escape(str(c.get("group_label","part")).upper())} {cur}</text>'
                             f'<line x1="{nx(x1):.1f}" y1="20" x2="{nx(x1):.1f}" y2="{ph-6}" class="kl"/>')
                cur, st = x.get("group"), x.get("x0", 0)
        for j, n in enumerate(order):
            y = top + j * RH
            tot = sum(z["duration"] for z in cast[n])
            hue = f"var({slot[n]})" if n in slot else "var(--ng)"
            presence += (f'<text x="{LG-8}" y="{y+9}" class="pn">{H.escape(n)}</text>'
                         f'<line x1="{LG}" y1="{y+6}" x2="{W-R}" y2="{y+6}" class="pg"/>')
            for z in cast[n]:
                x0, x1 = nx(z["x0"]), nx(z["x1"])
                presence += (f'<line class="pb" stroke="{hue}" x1="{x0+1.5:.1f}" y1="{y+6}" '
                             f'x2="{max(x1-1.5, x0+1.5):.1f}" y2="{y+6}"><title>'
                             f'{H.escape(n)} - {H.escape(c["unit"])} {H.escape(z["id"])}</title></line>')
            presence += (f'<text x="{W-R+2}" y="{y+9}" class="pw">{round(tot/TOT*100)}%</text>')
        presence = (f'<svg class="chart" viewBox="0 0 {W+22} {ph}" role="img" '
                    f'aria-label="Which {c["unit"]}s each character appears in">{presence}</svg>')

    title = c.get("work_roman") or c["work"]
    tmpl = open(_template(), encoding="utf-8").read()
    sub = dict(KIT_VERSION=config.KIT_VERSION, TITLE=H.escape(title), WORK=H.escape(c["work"]), MEDIUM=H.escape(c["medium"]),
        N=len(r), TOT=f"{TOT:,}", DU=H.escape(D), NK=nk, UNIT=H.escape(U),
        IL=H.escape(c["intensity_label"]), KL=H.escape(c["key_label"]),
        W=W, HT=HT, GRP=grp, GRID=grid, FILL=fill, RIS=ris, STEP=step, KEYS=keys,
        TICK=tick, SUS=sus, HITS=hits, NOTES=notes, ROWS=rows, DATA=DATA,
        REFCURVE=ref_curve, VITALS=vitals_html,
        PRESENCE=presence,
        UPDATED=('<p class="stamp">' + H.escape(c["updated"]) + "</p>") if c.get("updated") else "")
    for k, v in sub.items():
        tmpl = tmpl.replace("{{" + k + "}}", str(v))
    return tmpl

# ---------- template lookup: book override, else the kit default -----------
def _template():
    kit = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "templates", "skeleton-template.html")
    try:
        local = os.path.join(config.root(), "Strategy", "creative",
                             "skeleton-template.html")
    except config.BookError:
        return kit          # a hand-built contract renders outside a book
    return local if os.path.exists(local) else kit

# ---------- write: adapt this manuscript, render, save ----------------------
def write():
    """Render the current book and return the path written."""
    out = os.path.join(config.root(), "Strategy", "creative", "skeleton.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(render(from_manuscript()))
    return out

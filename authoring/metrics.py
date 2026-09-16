def total_duration(rows):
    return sum(r["duration"] for r in rows)

def cumulative_positions(rows):
    """Returns a list of cumulative words BEFORE each scene."""
    cum = 0
    cums = []
    for r in rows:
        cums.append(cum)
        cum += r["duration"]
    return cums

def row_midpoint(row, cum_before):
    return cum_before + row["duration"] / 2

def peak_position(rows):
    """Returns (peak_index, peak_row, peak_midpoint_fraction)"""
    if not rows:
        return -1, None, 0.0
    tot = total_duration(rows)
    cums = cumulative_positions(rows)
    peak_idx = max(range(len(rows)), key=lambda i: rows[i]["intensity"])
    peak_row = rows[peak_idx]
    mid = row_midpoint(peak_row, cums[peak_idx])
    return peak_idx, peak_row, (mid / tot) if tot else 0.0

def group_duration_shares(rows):
    """Returns [(group_name, share_fraction, duration)] ordered by appearance."""
    tot = total_duration(rows)
    if not tot:
        return []
    groups = []
    for x in rows:
        g = x.get("group")
        if g is not None:
            if not groups or groups[-1][0] != g:
                groups.append([g, 0])
            groups[-1][1] += x["duration"]
    return [(g, d / tot, d) for g, d in groups]

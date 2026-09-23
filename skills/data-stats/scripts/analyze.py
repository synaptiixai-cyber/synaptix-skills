"""
data-stats :: analyze.py
========================
AST-sandboxed statistical analysis script for the Synaptix data-stats skill.

Inputs (injected by SkillScriptRunner into the exec namespace):
    inputs["data"] — one of:
        - list[float | int]               flat dataset
        - dict[str, list[float | int]]    named columns

Output (set result["output"] or print JSON):
    JSON string with per-column stats.

Stdlib only: json, math, statistics, collections, sorted, enumerate.
No imports beyond what SkillScriptRunner allows.
"""

import json
import math
import statistics
import collections


def analyze_column(name, values):
    """Compute full stats for a single numeric column."""
    n = len(values)
    if n == 0:
        return {"column": name, "error": "Empty dataset"}

    sorted_vals = sorted(values)
    col = {"column": name, "count": n}

    # Basic stats
    col["min"] = sorted_vals[0]
    col["max"] = sorted_vals[-1]
    col["mean"] = round(statistics.mean(values), 4)
    col["median"] = round(statistics.median(values), 4)

    if n >= 2:
        col["std_dev"] = round(statistics.stdev(values), 4)
    else:
        col["std_dev"] = None

    # Percentiles (manual — statistics.quantiles needs Python 3.8+, use linear interp)
    def percentile(data, p):
        idx = (len(data) - 1) * p / 100
        lo, hi = int(idx), min(int(idx) + 1, len(data) - 1)
        frac = idx - lo
        return round(data[lo] + frac * (data[hi] - data[lo]), 4)

    if n >= 4:
        col["p25"] = percentile(sorted_vals, 25)
        col["p75"] = percentile(sorted_vals, 75)
        col["iqr"] = round(col["p75"] - col["p25"], 4)
    else:
        col["p25"] = col["p75"] = col["iqr"] = None

    # Top / bottom 3
    col["top3"] = sorted_vals[-3:][::-1]
    col["bottom3"] = sorted_vals[:3]

    # Z-score outliers (|z| > 2) — only when std_dev is meaningful
    if col["std_dev"] and col["std_dev"] > 0:
        mean = col["mean"]
        sd = col["std_dev"]
        outliers = []
        for v in values:
            z = (v - mean) / sd
            if abs(z) > 2:
                outliers.append({"value": v, "z": round(z, 2)})
        col["outliers"] = sorted(outliers, key=lambda x: abs(x["z"]), reverse=True)
    else:
        col["outliers"] = []

    return col


# ── Main ──────────────────────────────────────────────────────────────────────

raw = inputs.get("data")  # injected by SkillScriptRunner

if raw is None:
    output = json.dumps({"error": "No 'data' key in inputs"})

elif isinstance(raw, list):
    # Flat dataset
    try:
        values = [float(v) for v in raw]
        result = analyze_column("Dataset", values)
        output = json.dumps({"columns": [result]})
    except (TypeError, ValueError) as e:
        output = json.dumps({"error": f"Could not parse flat list: {e}"})

elif isinstance(raw, dict):
    # Named columns
    columns = []
    for col_name, col_values in raw.items():
        try:
            values = [float(v) for v in col_values]
            columns.append(analyze_column(col_name, values))
        except (TypeError, ValueError) as e:
            columns.append({"column": col_name, "error": str(e)})
    output = json.dumps({"columns": columns})

else:
    output = json.dumps({"error": f"Unsupported data type: {type(raw).__name__}"})

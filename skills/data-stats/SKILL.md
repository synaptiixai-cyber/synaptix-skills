---
name: data-stats
version: 1.0.0
description: >
  Statistical analysis of numeric datasets. Computes summary statistics
  (mean, median, std dev, min, max, percentiles), identifies top and bottom
  performers, and flags outliers using z-score detection.
  Accepts flat lists or named column datasets. Returns a structured markdown report.
risk: none
env_required: []
tags:
  - data
  - analytics
  - python
  - statistics
author: Synaptix
---

# Data Statistics Skill

Perform rigorous statistical analysis on any numeric dataset the user provides.
No external APIs. No credentials. Pure deterministic computation.

## When to Use This Skill

Use this skill when the user provides numeric data and asks for:
- Summary statistics (mean, median, std dev, range)
- Distribution analysis (percentiles, quartiles)
- Top / bottom N performers
- Outlier or anomaly detection
- Comparison across multiple data columns

## Input Format

The user's brief must contain the dataset. Accept any of these formats:

**Flat list:**
```
Analyze this: [120, 340, 89, 450, 210, 95, 600, 33]
```

**Named columns (e.g. sales by region):**
```
North: [120, 340, 89, 450]
South: [210, 95, 600, 33]
East: [510, 280, 190, 420]
```

**JSON:**
```json
{"revenue": [12000, 45000, 8900], "costs": [9000, 31000, 7200]}
```

## Execution Steps

1. **Parse the brief** — extract the dataset(s). Determine if it is a flat list
   or named columns. If ambiguous, make a reasonable assumption and state it.

2. **Call `run_script`** with the extracted data:
   ```
   run_script(
     script_path="scripts/analyze.py",
     inputs={
       "data": <flat list  OR  dict of column_name → list>
     }
   )
   ```

3. **Format the result** — render the returned JSON as a clean markdown report
   with tables, bullet points, and a plain-English insight per column.

## Output Format

```
## Statistical Analysis Report

### [Column Name or "Dataset"]
| Metric      | Value  |
|-------------|--------|
| Count       | N      |
| Mean        | X.XX   |
| Median      | X.XX   |
| Std Dev     | X.XX   |
| Min         | X.XX   |
| Max         | X.XX   |
| 25th pct    | X.XX   |
| 75th pct    | X.XX   |

**Top 3:** value, value, value
**Bottom 3:** value, value, value
**Outliers (|z| > 2):** value (z=X.X), ...  — or "None detected"

> Plain-English insight: one sentence summarising the key finding.
```

## Error Handling

- Cannot parse data → ask user to clarify format.
- Fewer than 3 values → skip std dev and percentiles; state why.
- No outliers → "No outliers detected."
- Never invent data. Only compute what was provided.

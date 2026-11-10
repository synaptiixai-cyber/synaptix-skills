# Template: `line-chart`

Multi-series trend chart over time or ordered categories (`1..3` series, `3..12` points each).

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `series` | yes | Array of `1..3` series objects; **all series must have the same number of points** |
| `series[s].name` | yes | Series legend name `<= 24` chars |
| `series[s].points` | yes | Array of `3..12` objects: `{"x", "y"}` |
| `series[s].points[p].x` | yes | X-axis tick label `<= 10` chars (e.g. `"Q1"`, `"2024"`, `"Wk 4"`) |
| `series[s].points[p].y` | yes | Finite number or safe arithmetic string |
| `y_label` | no | Axis caption `<= 32` chars |

## Example Spec
```json
{
  "template": "line-chart",
  "eyebrow": "ADOPTION CURVE",
  "title": "Monthly Active Workspaces vs Churn",
  "theme": "dark",
  "aspect": "wide",
  "data_kind": "sourced",
  "source": "Product analytics warehouse, FY25",
  "content": {
    "y_label": "Indexed growth",
    "series": [
      {
        "name": "Enterprise",
        "points": [
          {"x": "Q1", "y": 120},
          {"x": "Q2", "y": 165},
          {"x": "Q3", "y": 218},
          {"x": "Q4", "y": 290}
        ]
      },
      {
        "name": "Self-Serve",
        "points": [
          {"x": "Q1", "y": 95},
          {"x": "Q2", "y": 118},
          {"x": "Q3", "y": 144},
          {"x": "Q4", "y": 176}
        ]
      }
    ]
  }
}
```

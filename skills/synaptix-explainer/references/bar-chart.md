# Template: `bar-chart`

Vertical bar comparison for discrete categories (`2..8` bars).

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `items` | yes | Array of `2..8` objects: `{"label", "value", "unit"?}` |
| `items[i].label` | yes | Category label `<= 18` chars |
| `items[i].value` | yes | Non-negative number (`>= 0`) or safe arithmetic string (e.g. `"120+15"`) |
| `items[i].unit` | no | Short suffix `<= 10` chars (e.g. `"%"`, `"ms"`, `"$M"`) |
| `y_label` | no | Axis caption `<= 32` chars |

## Example Spec
```json
{
  "template": "bar-chart",
  "eyebrow": "LATENCY BENCHMARK",
  "title": "P95 Query Latency by Storage Tier",
  "theme": "light",
  "aspect": "wide",
  "data_kind": "sourced",
  "source": "Internal load test run #408 (10k RPS)",
  "content": {
    "y_label": "Milliseconds (lower is faster)",
    "items": [
      {"label": "Edge KV", "value": 4.2, "unit": "ms"},
      {"label": "Redis Cluster", "value": 11.8, "unit": "ms"},
      {"label": "Read Replica", "value": 28.5, "unit": "ms"},
      {"label": "Primary DB", "value": 44.0, "unit": "ms"}
    ]
  }
}
```

# Template: `donut-chart`

Proportional breakdown of parts of a single whole (`2..6` slices, percentages computed automatically).

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `items` | yes | Array of `2..6` slice objects: `{"label", "value"}` |
| `items[i].label` | yes | Slice name `<= 20` chars |
| `items[i].value` | yes | Strictly positive number (`> 0`) or safe arithmetic string |
| `center_label` | no | Short label inside donut hole `<= 24` chars (defaults to `"TOTAL"`) |

## Example Spec
```json
{
  "template": "donut-chart",
  "eyebrow": "CLOUD FINOPS",
  "title": "Monthly Infrastructure Spend Share",
  "theme": "paper",
  "aspect": "wide",
  "data_kind": "sourced",
  "source": "AWS Cost Explorer, March billing close",
  "content": {
    "center_label": "USD $84K",
    "items": [
      {"label": "GPU Inference", "value": 38},
      {"label": "Managed Postgres", "value": 22},
      {"label": "Kubernetes Nodes", "value": 15},
      {"label": "Object Storage", "value": 9}
    ]
  }
}
```

# Template: `recap`

Executive summary / closing takeaways card (`2..5` numbered insights).

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `points` | yes | Array of `2..5` takeaway objects: `{"title", "detail"?}` |
| `points[i].title` | yes | Takeaway headline `<= 36` chars |
| `points[i].detail` | no | Supporting sentence `<= 90` chars |

## Example Spec
```json
{
  "template": "recap",
  "eyebrow": "EXECUTIVE SUMMARY",
  "title": "Three Rules for Reliable Agent Tooling",
  "theme": "paper",
  "aspect": "wide",
  "data_kind": "illustrative",
  "footer": "Synaptix Architecture Guidelines",
  "content": {
    "points": [
      {
        "title": "Validate All Errors in One Pass",
        "detail": "Return every broken field path together so the model repairs specs in one retry."
      },
      {
        "title": "Keep Layout Math Deterministic",
        "detail": "Let code compute coordinates, wrapping, and WCAG contrast instead of freehand SVG."
      },
      {
        "title": "Mark Unsourced Numbers Clearly",
        "detail": "Separate real cited figures from illustrative examples to preserve user trust."
      }
    ]
  }
}
```

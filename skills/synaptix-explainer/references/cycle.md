# Template: `cycle`

Continuous repeating loop (`3..6` stages arranged around an orbital ring) with curved arrows and flow pulses.

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `stages` | yes | Array of `3..6` stage objects: `{"title", "detail"?}` |
| `stages[i].title` | yes | Stage title `<= 28` chars |
| `stages[i].detail` | no | Stage description `<= 80` chars |
| `center` | no | Short core loop label inside ring `<= 28` chars |

## Example Spec
```json
{
  "template": "cycle",
  "eyebrow": "FLYWHEEL",
  "title": "RLHF Model Quality Improvement Loop",
  "theme": "paper",
  "aspect": "wide",
  "data_kind": "illustrative",
  "content": {
    "center": "Continuous Eval",
    "stages": [
      {"title": "Sample Prompts", "detail": "Collect hard production edge cases."},
      {"title": "Rank Responses", "detail": "Annotators score pairwise outputs."},
      {"title": "Train Reward", "detail": "Fit preference model on deltas."},
      {"title": "Policy Update", "detail": "Fine-tune and ship gated checkpoint."}
    ]
  }
}
```

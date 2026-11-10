# Template: `process`

Ordered sequential step workflow (`3..6` steps) with directional connectors and animated flow pulses.

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `steps` | yes | Array of `3..6` step objects: `{"title", "detail"?, "icon"?}` |
| `steps[i].title` | yes | Step headline `<= 28` chars |
| `steps[i].detail` | no | Concise explanation `<= 80` chars |
| `steps[i].icon` | no | Valid icon id (`check`, `bolt`, `shield`, `clock`, `cloud`, `database`, `user`, `chart`, `gear`, `globe`, `lock`, `star`) |

## Example Spec
```json
{
  "template": "process",
  "eyebrow": "RELEASE PIPELINE",
  "title": "How Canary Deployments Reach Production",
  "theme": "ink",
  "aspect": "wide",
  "data_kind": "illustrative",
  "content": {
    "steps": [
      {"title": "Build & Sign", "detail": "Compile immutable image and attach SBOM provenance.", "icon": "lock"},
      {"title": "5% Canary Traffic", "detail": "Route a small live slice while watching error budgets.", "icon": "chart"},
      {"title": "Automated Gate", "detail": "Compare P99 latency and 5xx rate over 15 minutes.", "icon": "shield"},
      {"title": "Full Rollout", "detail": "Shift 100% of traffic or instant-rollback on breach.", "icon": "check"}
    ]
  }
}
```

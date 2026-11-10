# Template: `timeline`

Chronological milestone spine (`3..7` dated or ordered events).

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `events` | yes | Array of `3..7` event objects: `{"when", "title", "detail"?}` |
| `events[i].when` | yes | Short date/phase badge `<= 12` chars (e.g. `"2023"`, `"Phase 1"`, `"Day 30"`) |
| `events[i].title` | yes | Milestone title `<= 28` chars |
| `events[i].detail` | no | Milestone note `<= 70` chars |

## Example Spec
```json
{
  "template": "timeline",
  "eyebrow": "MIGRATION ROADMAP",
  "title": "Monolith to Event-Driven Cutover",
  "theme": "light",
  "aspect": "wide",
  "data_kind": "illustrative",
  "content": {
    "events": [
      {"when": "Weeks 1-2", "title": "Outbox Dual-Write", "detail": "Publish domain events from existing transactions."},
      {"when": "Weeks 3-4", "title": "Shadow Consumers", "detail": "Verify projection parity without serving reads."},
      {"when": "Week 6", "title": "Read Cutover", "detail": "Switch API queries to materialized service views."},
      {"when": "Week 8", "title": "Retire Legacy Tables", "detail": "Drop monolith write paths after 14-day soak."}
    ]
  }
}
```

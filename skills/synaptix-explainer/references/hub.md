# Template: `hub`

Central core concept connected radially to `3..6` supporting spokes/pillars.

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `center` | yes | Object `{"title", "detail"?}` for the central hub card |
| `center.title` | yes | Core concept name `<= 28` chars |
| `center.detail` | no | Core summary `<= 80` chars |
| `spokes` | yes | Array of `3..6` spoke objects: `{"title", "detail"?, "icon"?}` |
| `spokes[i].title` | yes | Spoke title `<= 28` chars |
| `spokes[i].detail` | no | Spoke description `<= 80` chars |
| `spokes[i].icon` | no | Valid icon id (`check`, `bolt`, `shield`, `clock`, `cloud`, `database`, `user`, `chart`, `gear`, `globe`, `lock`, `star`) |

## Example Spec
```json
{
  "template": "hub",
  "eyebrow": "PLATFORM ARCHITECTURE",
  "title": "Four Pillars of Observable Services",
  "theme": "dark",
  "aspect": "wide",
  "data_kind": "illustrative",
  "content": {
    "center": {
      "title": "OpenTelemetry Core",
      "detail": "Unified SDK correlating signals via shared trace context."
    },
    "spokes": [
      {"title": "Metrics", "detail": "RED counters and SLO burn alerts.", "icon": "chart"},
      {"title": "Distributed Traces", "detail": "End-to-end request waterfall spans.", "icon": "bolt"},
      {"title": "Structured Logs", "detail": "JSON events indexed by trace_id.", "icon": "database"},
      {"title": "Continuous Profiles", "detail": "CPU and heap flamegraphs in prod.", "icon": "gear"}
    ]
  }
}
```

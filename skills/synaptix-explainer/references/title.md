# Template: `title`

Editorial hero opener card for keynotes, section breaks, or bold thesis statements.

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `subtitle` | no | Plain text `<= 100` chars |
| `icon` | no | One of: `check`, `bolt`, `shield`, `clock`, `cloud`, `database`, `user`, `chart`, `gear`, `globe`, `lock`, `star` |

No unknown keys allowed. Top-level `title` (`<= 60` chars) renders as the centered hero headline.

## Example Spec
```json
{
  "template": "title",
  "eyebrow": "ARCHITECTURE BRIEFING",
  "title": "Zero-Trust Identity at the Edge",
  "theme": "ink",
  "aspect": "wide",
  "data_kind": "illustrative",
  "footer": "Engineering Strategy · Q4",
  "content": {
    "subtitle": "Replacing perimeter firewalls with cryptographic workload attestation across every request.",
    "icon": "shield"
  }
}
```

# Template: `comparison`

Side-by-side option cards (`2..3` columns) with bullet points and an optional bottom verdict banner.

## `content` Contract
| Field | Required | Constraints |
|---|---|---|
| `columns` | yes | Array of `2..3` column objects: `{"title", "points", "icon"?}` |
| `columns[c].title` | yes | Option header `<= 28` chars |
| `columns[c].points` | yes | Array of `2..5` bullet strings, each `<= 60` chars |
| `columns[c].icon` | no | Valid icon id (`check`, `bolt`, `shield`, `clock`, `cloud`, `database`, `user`, `chart`, `gear`, `globe`, `lock`, `star`) |
| `verdict` | no | Concluding recommendation banner `<= 80` chars |

## Example Spec
```json
{
  "template": "comparison",
  "eyebrow": "RETRIEVAL DESIGN",
  "title": "BM25 Lexical Search vs Hybrid Vector RAG",
  "theme": "paper",
  "aspect": "wide",
  "data_kind": "illustrative",
  "content": {
    "columns": [
      {
        "title": "BM25 Lexical Only",
        "icon": "database",
        "points": [
          "Sub-10ms keyword lookup with zero embedding cost",
          "Exact SKU, code symbol, and acronym precision",
          "Misses paraphrases and cross-lingual synonyms"
        ]
      },
      {
        "title": "Hybrid + Reranker",
        "icon": "bolt",
        "points": [
          "Combines dense recall with exact term matching",
          "Handles natural-language questions reliably",
          "Adds ~45ms embedding + cross-encoder latency"
        ]
      }
    ],
    "verdict": "Use Hybrid + Reranker for user Q&A; keep BM25 for exact identifier lookup."
  }
}
```

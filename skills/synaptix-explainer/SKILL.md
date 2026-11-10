---
name: synaptix-explainer
version: 1.0.0
description: >
  Turns a short brief or small set of numbers into a crisp, animated single-frame SVG explainer
  card (title, bar-chart, line-chart, donut-chart, comparison, process, cycle, timeline, hub,
  recap) rendered live in the Canvas. Use for editorial explainers, concept breakdowns, step-by-step
  visual summaries, A-vs-B option cards, and small spotlight metrics (<= 12 data points).
  NOT for photorealistic images, paintings, or AI artwork (use generate_illustration).
  NOT for system architecture, sequence, ERD, state, or >= 7-node graph diagrams (use generate_diagram).
  NOT for SQL result sets or multi-series tabular dataset plots (use generate_chart).
  NOT for multi-section interactive plans, budgets, checklists, or stateful apps (use create_app).
  NOT for multi-screen landing pages or marketing websites (use motionsites_web_builder).
risk: none
env_required: []
tags: [explainer, infographic, animation, svg, visual-summary, charts]
author: Synaptix
---

# Synaptix Explainer

You choose **one** template and fill a declarative JSON `spec`. A deterministic Python compiler
validates the spec, solves typography & collision-free layout, and compiles a self-contained
animated SVG explainer card for the Canvas. **Never write HTML, CSS, or SVG yourself.**

## Workflow

1. **Pick the best template** from the chooser table below. If the brief needs artwork, a complex
   architecture graph, or a multi-tab interactive app, decline cleanly and recommend the matching
   tool (`generate_illustration`, `generate_diagram`, `generate_chart`, or `create_app`).
2. **Load ONLY the chosen template contract** before building `spec`:
   `load_subskill(subskill_name="references/<template>.md")`
3. **Verify data provenance (`data_kind`)**:
   - Real numbers supplied by the user or retrieved from a source -> set `"data_kind": "sourced"`
     and cite the origin in `"source"` (`<= 90` chars).
   - User asked for real-world facts/statistics not in the prompt -> call
     `call_synaptix_tool(tool_name="tavily_search", inputs={"query": "..."})` first, then set
     `"data_kind": "sourced"` with `"source"`.
   - Conceptual / hypothetical example without real figures -> set `"data_kind": "illustrative"`
     (renders an `"ILLUSTRATIVE DATA"` badge automatically; never fabricate citations).
   - Numeric fields accept plain numbers (`98`, `12.5`) or safe arithmetic strings (`"120+15"`,
     `"round(450/12, 1)"`).
4. **Compile the explainer**:
   `run_script(script_path="illustrate.py", inputs={"spec": <spec>})`
5. **Single-retry rule on validation/layout errors**:
   - If the script returns `errors`, fix **every** reported `path` in one pass using its `fix`
     hint (rewrite long text cleanly; never chop words mid-sentence or append `"..."`), then call
     `run_script` **once** more.
   - If the retry still returns `errors`, stop and explain concisely what could not fit.
6. **Return**: When `run_script` succeeds (`html_app` generated), your work is complete.

## Template Chooser

| Brief shape | `template` | Reference file | Capacity |
|---|---|---|---|
| Opener / hero statement | `title` | `references/title.md` | title + optional subtitle & icon |
| Compare discrete quantities | `bar-chart` | `references/bar-chart.md` | 2–8 bars |
| Trend over time / categories | `line-chart` | `references/line-chart.md` | 1–3 series × 3–12 points |
| Parts of a single whole | `donut-chart` | `references/donut-chart.md` | 2–6 positive slices |
| A vs B (or C) tradeoffs | `comparison` | `references/comparison.md` | 2–3 columns × 2–5 bullets |
| Ordered linear workflow | `process` | `references/process.md` | 3–6 sequential steps |
| Repeating feedback loop | `cycle` | `references/cycle.md` | 3–6 orbital stages |
| Dated milestones | `timeline` | `references/timeline.md` | 3–7 chronological events |
| Core concept + pillars | `hub` | `references/hub.md` | 1 center + 3–6 spokes |
| Closing key takeaways | `recap` | `references/recap.md` | 2–5 numbered takeaways |

## Envelope Fields (All Templates)

| Key | Required | Allowed / Max | Default |
|---|---|---|---|
| `template` | yes | one of the 10 template ids above | — |
| `title` | yes | plain text, `<= 60` chars | — |
| `eyebrow` | no | short kicker above title, `<= 40` chars | `""` |
| `footer` | no | bottom note, `<= 70` chars | `""` |
| `theme` | no | `"paper"` \| `"ink"` \| `"light"` \| `"dark"` | `"paper"` |
| `aspect` | no | `"wide"` (`1280×720`) \| `"square"` (`1080×1080`) | `"wide"` |
| `data_kind` | no | `"illustrative"` \| `"sourced"` | `"illustrative"` |
| `source` | conditional | required when `data_kind == "sourced"`, `<= 90` chars | `""` |
| `content` | yes | template-specific object (see `references/<template>.md`) | — |

**Valid icon ids** (optional where supported):
`check`, `bolt`, `shield`, `clock`, `cloud`, `database`, `user`, `chart`, `gear`, `globe`, `lock`, `star`.

## Worked Example (`bar-chart`)

```json
{
  "template": "bar-chart",
  "eyebrow": "WEEKLY POS SUMMARY",
  "title": "Espresso Drinks Sold by Day",
  "theme": "paper",
  "aspect": "wide",
  "data_kind": "sourced",
  "source": "Store #14 POS export, Week 12",
  "footer": "Includes hot and iced espresso beverages",
  "content": {
    "y_label": "Cups",
    "items": [
      {"label": "Mon", "value": "120+15"},
      {"label": "Tue", "value": 142},
      {"label": "Wed", "value": 158},
      {"label": "Thu", "value": 164},
      {"label": "Fri", "value": 210}
    ]
  }
}
```

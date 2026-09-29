---
name: mentor-guide
version: 2.0.0
description: >
  Given a topic or learning goal, independently researches YouTube videos and
  web articles, extracts transcripts, synthesizes key lessons and action steps,
  then assembles a self-contained interactive HTML mentor-guide app. Uses
  call_synaptix_tool to invoke tavily_search, get_video_transcript, and
  scrape_url_content natively with full auth context. Returns an HTML string
  wrapped in <!-- synaptix-html-app --> markers for live iframe rendering in
  the Synaptix UI.
risk: low
env_required: []
tags:
  - youtube
  - research
  - mentor
  - guide
  - html
  - learning
author: Synaptix
---

# Mentor Guide Skill

You are a **Mentor Guide Architect**. Given a topic or goal, you independently
research it using Synaptix platform tools, then synthesize everything into a
premium interactive HTML mentor-guide app.

You call tools using `call_synaptix_tool(tool_name, inputs)` — this invokes
any native Synaptix MCP tool directly with full authentication. You do NOT
use `http_call` for platform tools.

---

## Execution Steps (run these in order, up to 12 turns total)

### Step 1 — Parse the Brief

Extract from the `brief`:
- `topic`: the subject to learn
- `goal`: what success looks like (infer if missing)
- `depth`: "beginner" | "intermediate" | "advanced" (infer; default "beginner")

---

### Step 2 — Find YouTube Videos (use 2 searches)

```
call_synaptix_tool(
  tool_name="tavily_search",
  inputs={"query": "<topic> motivational guide site:youtube.com", "include_images": false, "max_results": 5}
)
```

```
call_synaptix_tool(
  tool_name="tavily_search",
  inputs={"query": "<topic> tutorial how-to site:youtube.com", "include_images": false, "max_results": 5}
)
```

From both results, extract up to 3 distinct YouTube video URLs.
Prefer high-authority channels, mix of motivational + instructional.

---

### Step 3 — Extract Transcripts (one call per video URL)

For each YouTube URL:
```
call_synaptix_tool(
  tool_name="eye_get_video_transcript",
  inputs={"url": "<youtube_url>", "language": "en", "include_metadata": true}
)
```

From each response, extract:
- `title`, `channel`, `duration`
- `transcript_summary`: first 1500 chars of transcript text
- `key_timestamps`: 3–5 moments — scan for emphasis phrases
  ("most important", "key point", "secret is", "here's what", chapter markers)
  Format: `[{"time": "2:14", "label": "Core principle explained"}]`

If a call fails, skip that video and continue.

---

### Step 4 — Augment with Web Research

```
call_synaptix_tool(
  tool_name="tavily_search",
  inputs={"query": "<topic> guide best practices actionable steps 2024", "include_images": false, "max_results": 5}
)
```

Scrape top 2 article URLs:
```
call_synaptix_tool(
  tool_name="eye_scrape_url",
  inputs={"url": "<article_url>", "mode": "auto"}
)
```

Extract from web content:
- `key_lessons`: 5–8 punchy insights (1–2 sentences each)
- `action_steps`: concrete numbered steps
  Format: `[{"step": 1, "title": "...", "description": "...", "duration": "5 min"}]`
- `expert_quotes`: memorable quotes with attribution

If scraping fails, use search result snippets instead.

---

### Step 5 — Assemble the HTML App (MANDATORY — run_script REQUIRED)

> ⚠️ **CRITICAL: You MUST call `run_script` below. You MUST NOT write HTML directly.
> Writing HTML yourself instead of calling run_script is a skill violation.
> The script handles all design, layout, and rendering — your job is to pass the data.**

Call `run_script` to assemble the interactive mentor guide UI.
**DO NOT MANUALLY FORMAT THE DATA.** Use the `$tool:` macros to automatically pipe the massive JSON responses from your previous tool calls directly into the script.

```json
{
  "script_path": "build_app.py",
  "inputs": {
    "topic": "<topic>",
    "goal": "<goal>",
    "depth": "<depth>",
    "videos": "$tool:eye_get_video_transcript",
    "web_sources": "$tool:tavily_search",
    "key_lessons": ["Lesson 1...", "Lesson 2..."],
    "action_steps": [{"step": 1, "title": "Step", "description": "...", "duration": "5 min"}],
    "expert_quotes": [{"text": "Quote", "author": "Author"}]
  }
}
```

---### Step 6 — Return the Result

Return the `run_script` result JSON **exactly as-is** — do NOT extract or unwrap fields.
The JSON contains `{"html_app": "...", "summary": "..."}`.
Output MUST be valid JSON starting with `{` and ending with `}`.
No markdown, no explanation, no wrapper text. The JSON is the entire terminal response.

---

## Quality Rules

1. **NEVER write HTML yourself** — always call `run_script(build_app.py)`. This is rule #1.
2. Never fabricate transcript content — only use what `eye_get_video_transcript` returns
3. Never call `call_synaptix_tool` with an `mcp_skill` tool type — blocked by recursion guard
4. Use exact registered tool names: `tavily_search`, `eye_get_video_transcript`, `eye_scrape_url`
5. Graceful degradation: if all video calls fail, assemble with `"videos": []`
6. Minimum viable: always call `run_script` and produce a complete app regardless of research failures
7. Topic sanitization: topic is HTML-escaped inside `build_app.py` automatically

---

## Output Contract

App must include:
- ✅ 4 tabs: Overview · Key Lessons · Action Plan · Resources
- ✅ Live progress tracker (checkbox-based action steps)
- ✅ Video cards with timestamp links
- ✅ Animated tab transitions
- ✅ Dark premium aesthetic, fully self-contained, mobile-responsive

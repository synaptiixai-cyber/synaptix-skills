"""
build_app.py - Mentor Guide HTML app builder (v6.0, production)

Runtime contract (unchanged):
  - Executed by SkillExecutor via run_script(); a global `inputs` dict is injected.
  - stdlib only: json, re, html, hashlib.
  - Sets a global `result` dict: {"html_app": str, "summary": str, "warnings": [str]}
  - html_app is wrapped in <!-- synaptix-html-app --> ... <!-- /synaptix-html-app -->

v6 turns the learning guide into a general guide builder. All new inputs are
OPTIONAL; payloads from v5 render as before.
  - archetype + labels: wording that fits the topic (trip, project, habit ...)
  - notice + assumptions + lang
  - new sections: schedule (days/phases), checklist, budget (live totals),
    deadlines
  - progress counts steps, schedule items, checklist items and deadlines
  - fixes: panel margin leak, panel focus ring, mobile tab scroll, 44px
    targets, print stylesheet; over-long quotes are dropped

Client state design (unchanged from v5, read before changing the JS):
  - The DOM is the source of truth. Every user-editable control carries a
    stable `data-f` key. Key families:
        s{i}-done|due|note   action steps       c{n}-title|done|due|note  user milestones
        l{i}-note            lessons            v{i}-note                  videos
        d{g}-{i}-done|note   schedule items     k{g}-{i}-done              checklist items
        b{i}-actual          budget actuals     x{i}-done                  deadlines
        target, target-text, journal
  - Drafts autosave to localStorage keyed by guide id AND version.
  - Journal entries are rebuilt from the DOM whenever the tab opens.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import re

# -- Config -------------------------------------------------------------------

MAX_ITEMS = 60          # per list
MAX_TEXT = 6000         # per text field
MAX_TITLE = 300
MAX_NOTE = 4000         # user note fields (textarea maxlength)
MAX_LABEL = 120         # user single-line fields
MAX_QUOTE_WORDS = 30    # longer quotes are dropped (copyright / fabrication guard)
# postMessage target for the save bar. "*" works anywhere but lets any parent
# frame read the user's notes; set to the host's exact origin in production.
SAVE_TARGET_ORIGIN = "*"
SAVE_MESSAGE_TYPE = "synaptix-html-app-save"
WEB_FONTS = True        # False => system fonts only, zero external requests
HUES = (4, 22, 150, 175, 200, 222, 340)   # avoids stock indigo/purple and lime
DEPTHS = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}

ARCHETYPES = {"learn_skill", "understand_subject", "exam_prep", "plan_trip",
              "plan_event", "build_project", "decision", "habit", "other"}
LABEL_DEFAULTS = {
    "overview": "Overview", "lessons": "Key lessons", "action": "Action plan",
    "schedule": "Schedule", "checklist": "Checklists", "budget": "Budget",
    "deadlines": "Deadlines", "step": "Step", "drill": "Practice drill", "tips": "Try this",
}
# Default wording per archetype. Explicit `labels` input overrides these.
ARCH_LABELS = {
    "understand_subject": {"drill": "Activity", "tips": "Key points"},
    "exam_prep": {"action": "Study plan", "drill": "Study task", "tips": "Key points"},
    "plan_trip": {"action": "Before you go", "drill": "Details", "tips": "Good to know", "step": "Task"},
    "plan_event": {"action": "Preparation", "drill": "Details", "tips": "Good to know", "step": "Task"},
    "build_project": {"action": "Milestones", "drill": "Deliverable", "tips": "Watch out for", "step": "Milestone"},
    "decision": {"action": "How to decide", "drill": "Do this", "tips": "Consider"},
    "habit": {"action": "Experiments", "drill": "Experiment", "tips": "Try this", "step": "Experiment"},
}
_L = dict(LABEL_DEFAULTS)   # active labels, reset once per build()

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_YT_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtu.be", "www.youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com",
}
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_TS = re.compile(r"^(?:\d{1,2}:)?\d{1,2}:\d{2}$")
_TS_LINE = re.compile(r"^\s*\[?((?:\d{1,2}:)?\d{1,2}:\d{2})\]?\s*[-\u2013\u2014:]?\s*(.*)$")
_LANG = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# -- Coercion helpers ---------------------------------------------------------

def esc(value) -> str:
    return _html.escape("" if value is None else str(value), quote=True)


def txt(value, limit: int = MAX_TEXT) -> str:
    """Coerce scalars to clean text. Containers are ignored, never stringified."""
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return ""
    s = _CTRL.sub("", str(value)).strip()
    return s[:limit].rstrip() if len(s) > limit else s


def clip(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(",;:.- ")
    return cut + "\u2026"


def as_list(value) -> list:
    """list | dict | JSON string | plain string | None -> list (capped)."""
    if value is None:
        return []
    if isinstance(value, str):
        v = value.strip()
        if v[:1] in "[{":
            try:
                return as_list(json.loads(v))
            except ValueError:
                pass
        return [v] if v else []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, (list, tuple)):
        return list(value)[:MAX_ITEMS]
    return []


def str_list(value, limit: int = 500) -> list:
    """Accept list of scalars, or a newline/bullet separated string."""
    out = []
    items = value if isinstance(value, (list, tuple)) else (
        re.split(r"\n+", value) if isinstance(value, str) else []
    )
    for item in items[:MAX_ITEMS]:
        t = re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s*", "", txt(item, limit))
        if t:
            out.append(t)
    return out


def first(d: dict, *keys, default=None):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return default


_URL_RE = re.compile(r"^(https?)://([^/?#:]+)(?::\d+)?(/[^?#]*)?(?:\?([^#]*))?", re.IGNORECASE)


def safe_url(url) -> str:
    """http(s) only, with a host. Anything else returns ''."""
    u = _CTRL.sub("", str(url or "")).strip()
    if not u or len(u) > 2048 or not _URL_RE.match(u):
        return ""
    return u


def youtube_id(url: str):
    u = _CTRL.sub("", str(url or "")).strip()
    m = _URL_RE.match(u)
    if not m:
        return None
    host = m.group(2).lower()
    if host not in _YT_HOSTS:
        return None
    path = m.group(3) or "/"
    query = m.group(4) or ""
    cand = None
    if host.endswith("youtu.be"):
        cand = path.lstrip("/")[:11]
    else:
        qv = re.search(r"(?:^|[?&])v=([^&#]+)", query)
        if qv:
            cand = qv.group(1)
        else:
            em = re.match(r"^/(?:embed|shorts|live|v)/([^/?#]+)", path)
            cand = em.group(1) if em else None
    return cand if cand and _YT_ID.match(cand) else None


def ts_seconds(ts: str):
    ts = txt(ts, 12)
    if ts.isdigit():
        return int(ts)
    if not _TS.match(ts):
        return None
    secs = 0
    for part in ts.split(":"):
        secs = secs * 60 + int(part)
    return secs


def topic_hue(topic: str) -> int:
    return HUES[int(hashlib.sha256(topic.encode("utf-8")).hexdigest(), 16) % len(HUES)]


def valid_date(d: str) -> bool:
    return bool(_DATE.match(d)) and 1 <= int(d[5:7]) <= 12 and 1 <= int(d[8:10]) <= 31


# -- Normalizers --------------------------------------------------------------

def norm_blueprint(inputs, warn):
    a = txt(inputs.get("archetype"), 40).lower()
    if a and a not in ARCHETYPES:
        warn(f"unknown archetype '{a}'; using 'other'")
        a = "other"
    labels = dict(LABEL_DEFAULTS)
    labels.update(ARCH_LABELS.get(a, {}))
    raw = inputs.get("labels")
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k in LABEL_DEFAULTS and txt(v, 30):
                labels[k] = txt(v, 30)
    lang = txt(inputs.get("lang"), 12)
    return {
        "archetype": a or "learn_skill",
        "labels": labels,
        "notice": txt(inputs.get("notice"), 600),
        "assumptions": str_list(inputs.get("assumptions"), 160)[:8],
        "lang": lang if _LANG.match(lang) else "en",
    }


def norm_lessons(raw, warn):
    out = []
    for i, item in enumerate(as_list(raw)):
        if isinstance(item, dict):
            title = txt(first(item, "title", "name", default=""), MAX_TITLE)
            desc = txt(first(item, "description", "desc", "text", "lesson", default=""))
            tips = str_list(first(item, "tips", "key_points", "action_points", "takeaways", default=[]))
            source = txt(first(item, "source", "source_video", "channel", "author", default=""), 120)
        else:
            title, desc, tips, source = "", txt(item), [], ""
        if title or desc:
            out.append({"title": title, "desc": desc, "tips": tips, "source": source})
        else:
            warn(f"key_lessons[{i}] had no usable text and was skipped")
    return out


def norm_quotes(raw, warn):
    out = []
    for i, item in enumerate(as_list(raw)):
        if isinstance(item, dict):
            text, author = txt(first(item, "text", "quote", default=""), 600), txt(item.get("author", ""), 120)
        else:
            text, author = txt(item, 600), ""
        if not text:
            warn(f"expert_quotes[{i}] had no text and was skipped")
        elif len(text.split()) > MAX_QUOTE_WORDS:
            warn(f"expert_quotes[{i}] is longer than {MAX_QUOTE_WORDS} words and was skipped")
        else:
            out.append({"text": text, "author": author})
    return out


def norm_steps(raw, warn):
    out = []
    for i, item in enumerate(as_list(raw)):
        if isinstance(item, dict):
            title = txt(item.get("title", ""), MAX_TITLE)
            desc = txt(first(item, "description", "desc", default=""))
            dur = txt(item.get("duration", ""), 40)
            drill = txt(first(item, "details", "practice_drill", "drill", default=""))
        else:
            title, desc, dur, drill = txt(item, MAX_TITLE), "", "", ""
        if not (title or desc):
            warn(f"action_steps[{i}] had no usable text and was skipped")
            continue
        out.append({"title": title or f"{_L['step']} {len(out) + 1}", "desc": desc, "dur": dur, "drill": drill})
    return out


def _norm_timestamps(raw):
    out = []
    for item in as_list(raw):
        if isinstance(item, dict):
            t, label = txt(first(item, "time", "t", "timestamp", default=""), 12), txt(item.get("label", ""), 200)
        else:
            m = _TS_LINE.match(txt(item, 240))
            t, label = (m.group(1), m.group(2)) if m else ("", "")
        secs = ts_seconds(t)
        if secs is not None:
            out.append({"time": t, "secs": secs, "label": label})
    return out


def norm_videos(raw, warn):
    out, seen = [], set()
    for i, item in enumerate(as_list(raw)):
        if not isinstance(item, dict):
            warn(f"videos[{i}] is not an object and was skipped")
            continue
        url = safe_url(item.get("url"))
        if not url:
            warn(f"videos[{i}] has no valid http(s) url and was skipped")
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append({
            "url": url,
            "vid": youtube_id(url),
            "title": txt(item.get("title", ""), MAX_TITLE) or "Untitled video",
            "channel": txt(first(item, "channel", "author", default=""), 120),
            "duration": txt(item.get("duration", ""), 30),
            "summary": txt(first(item, "transcript_summary", "summary", default=""), 1200),
            "takeaways": str_list(first(item, "takeaways", "key_takeaways", "notes", default=[])),
            "stamps": _norm_timestamps(item.get("key_timestamps")),
        })
    return out


def norm_web(raw, warn):
    flat = []
    for item in as_list(raw):
        if isinstance(item, dict) and isinstance(item.get("results"), list):
            flat.extend(r for r in item["results"][:MAX_ITEMS] if isinstance(r, dict))
        else:
            flat.append(item)
    out, seen = [], set()
    for i, item in enumerate(flat):
        if not isinstance(item, dict):
            continue
        url = safe_url(item.get("url"))
        if not url:
            warn(f"web_sources[{i}] has no valid http(s) url and was skipped")
            continue
        if url in seen:
            continue
        seen.add(url)
        m_host = _URL_RE.match(url)
        host = (m_host.group(2).lower() if m_host else "").removeprefix("www.")
        out.append({"url": url, "title": txt(item.get("title", ""), MAX_TITLE) or host, "host": host})
    return out[:MAX_ITEMS]


def norm_schedule(raw, warn):
    out = []
    for gi, g in enumerate(as_list(raw)):
        if not isinstance(g, dict):
            warn(f"schedule[{gi}] is not an object and was skipped")
            continue
        items = []
        for it in as_list(first(g, "items", "activities", default=[])):
            if isinstance(it, dict):
                title = txt(first(it, "title", "name", default=""), MAX_TITLE)
                note = txt(first(it, "note", "details", "description", default=""), 800)
                time, verify = txt(it.get("time", ""), 40), bool(it.get("verify"))
            else:
                title, note, time, verify = txt(it, MAX_TITLE), "", "", False
            if title:
                items.append({"title": title, "note": note, "time": time, "verify": verify})
        if items:
            out.append({
                "title": txt(first(g, "title", "day", "phase", default=""), MAX_TITLE) or f"Day {len(out) + 1}",
                "summary": txt(g.get("summary", ""), 300),
                "items": items,
            })
        else:
            warn(f"schedule[{gi}] had no items and was skipped")
    return out


def norm_checklist(raw, warn):
    out = []
    for gi, g in enumerate(as_list(raw)):
        if not isinstance(g, dict):
            warn(f"checklist[{gi}] is not an object and was skipped")
            continue
        items = str_list(first(g, "items", default=[]), 200)
        if items:
            out.append({"title": txt(g.get("title", ""), MAX_TITLE) or "Checklist", "items": items})
        else:
            warn(f"checklist[{gi}] had no items and was skipped")
    return out


def _num(v):
    s = re.sub(r"[^0-9.]", "", "" if v is None or isinstance(v, (dict, list, bool)) else str(v))
    if not s:
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    return n if 0 <= n < 1e12 else None


def norm_budget(raw, warn):
    if not isinstance(raw, dict):
        return None
    items = []
    for i, it in enumerate(as_list(raw.get("items"))):
        if not isinstance(it, dict):
            continue
        label = txt(first(it, "label", "title", "name", default=""), 160)
        if label:
            items.append({"label": label, "est": _num(first(it, "estimate", "amount", default=None)),
                          "verify": bool(it.get("verify"))})
        else:
            warn(f"budget.items[{i}] had no label and was skipped")
    return {"cur": txt(raw.get("currency"), 8), "items": items} if items else None


def norm_deadlines(raw, warn):
    out = []
    for i, it in enumerate(as_list(raw)):
        if not isinstance(it, dict):
            continue
        title = txt(first(it, "title", "name", default=""), MAX_TITLE)
        if not title:
            warn(f"deadlines[{i}] had no title and was skipped")
            continue
        d = txt(it.get("date"), 10)
        if d and not valid_date(d):
            warn(f"deadlines[{i}] date '{d}' is not YYYY-MM-DD and was ignored")
            d = ""
        out.append({"title": title, "date": d, "note": txt(it.get("note", ""), 400)})
    out.sort(key=lambda x: (x["date"] == "", x["date"]))   # stable; keys follow this order
    return out


# -- Rendering ----------------------------------------------------------------

def paras(text: str) -> str:
    return "".join(f"<p>{esc(p.strip())}</p>" for p in re.split(r"\n\s*\n", text) if p.strip())


def render_quote(q: dict, cls: str = "quote") -> str:
    cite = f"<figcaption>{esc(q['author'])}</figcaption>" if q["author"] else ""
    return f'<figure class="{cls}"><blockquote><p>{esc(q["text"])}</p></blockquote>{cite}</figure>'


def note_box(field: str, empty_label: str, aria: str, placeholder: str = "") -> str:
    """Expandable in-place note. JS swaps the summary text and opens filled notes."""
    return (
        f'<details class="note"><summary data-empty="{esc(empty_label)}" data-filled="Your note">{esc(empty_label)}</summary>'
        f'<textarea class="note-input" data-f="{field}" maxlength="{MAX_NOTE}" rows="3" '
        f'aria-label="{esc(aria)}" placeholder="{esc(placeholder)}"></textarea></details>'
    )


def render_overview(ctx) -> str:
    c = ctx
    bp = c["bp"]
    level = f'<p class="level">{esc(c["level"])} guide</p>' if c["level"] else ""
    goal = c["goal"] or "Learn this topic and put it to work."
    hero_quote = render_quote(c["quotes"][0], "quote hero-quote") if c["quotes"] else ""

    sched_n = sum(len(g["items"]) for g in c["schedule"])
    check_n = sum(len(g["items"]) for g in c["checklist"])
    jumps = []
    for name, n, label in (
        ("lessons", len(c["lessons"]), _L["lessons"]),
        ("schedule", sched_n, _L["schedule"]),
        ("action", len(c["steps"]), _L["action"]),
        ("checklist", check_n, _L["checklist"]),
        ("budget", len(c["budget"]["items"]) if c["budget"] else 0, _L["budget"]),
        ("deadlines", len(c["deadlines"]), _L["deadlines"]),
        ("resources", len(c["videos"]) + len(c["web"]), "Resources"),
    ):
        if n:
            jumps.append(
                f'<li><button type="button" class="jump" data-goto="{name}">'
                f'{esc(label)} <strong>{n}</strong></button></li>'
            )
    jump_html = f'<ul class="jumps">{"".join(jumps)}</ul>' if jumps else ""

    notice = (f'<aside class="notice" role="note"><strong>Before you start.</strong> {esc(bp["notice"])}</aside>'
              if bp["notice"] else "")
    assume = ""
    if bp["assumptions"]:
        assume = ('<section class="assume" aria-labelledby="as-h"><h2 id="as-h">Assumptions</h2><ul>'
                  + "".join(f"<li>{esc(a)}</li>" for a in bp["assumptions"]) + "</ul></section>")

    preview = ""
    if c["lessons"]:
        rows = []
        for l in c["lessons"][:3]:
            head = l["title"] or clip(l["desc"], 70)
            body = clip(l["desc"], 170) if l["title"] else ""
            rows.append(f"<li><strong>{esc(head)}</strong>{(' ' + esc(body)) if body else ''}</li>")
        preview = f'<section class="preview" aria-labelledby="pv-h"><h2 id="pv-h">Worth knowing first</h2><ul>{"".join(rows)}</ul></section>'

    target = (
        '<div class="target">'
        '<label class="field" for="target-text"><span>Your finish line</span>'
        f'<input type="text" class="text-in" id="target-text" data-f="target-text" maxlength="{MAX_LABEL}" '
        'placeholder="What does success look like?"></label>'
        '<label class="field" for="target"><span>Target completion date</span>'
        '<input type="date" class="date" id="target" data-f="target"></label></div>'
    )

    return (
        '<section class="panel" id="panel-overview" role="tabpanel" aria-labelledby="tab-overview" tabindex="0">'
        f'<header class="hero"><div class="hero-meta">{level}<p class="ver" id="ver">Version 1, AI original</p></div>'
        f'<h1>{esc(c["topic"])}</h1><p class="goal">{esc(goal)}</p>{target}{hero_quote}</header>'
        f'{notice}{assume}{jump_html}{preview}</section>'
    )


def render_lessons(ctx) -> str:
    items = []
    for i, l in enumerate(ctx["lessons"]):
        title = f'<h3>{esc(l["title"])}</h3>' if l["title"] else ""
        src = f'<p class="source">From {esc(l["source"])}</p>' if l["source"] else ""
        tips = ""
        if l["tips"]:
            lis = "".join(f"<li>{esc(t)}</li>" for t in l["tips"])
            tips = f'<div class="tips"><p class="tips-h">{esc(_L["tips"])}</p><ul>{lis}</ul></div>'
        note = note_box(f"l{i}-note", "Add your own note", "Your note on this lesson", "How will you apply this?")
        items.append(f'<article class="lesson">{title}{src}<div class="prose">{paras(l["desc"])}</div>{tips}{note}</article>')
    quotes = ""
    if ctx["quotes"]:
        quotes = ('<section class="quotes" aria-labelledby="q-h"><h2 id="q-h">In their words</h2>'
                  + "".join(render_quote(q) for q in ctx["quotes"]) + "</section>")
    return (
        '<section class="panel" id="panel-lessons" role="tabpanel" aria-labelledby="tab-lessons" tabindex="0" hidden>'
        f'<h2 class="sr-only">{esc(_L["lessons"])}</h2>{"".join(items)}{quotes}</section>'
    )


def render_step(key: str, n: int, s: dict, custom: bool = False) -> str:
    """One action-plan row. `key` is s{i} for plan steps, c{n} for user milestones."""
    dur = f'<span>{esc(s["dur"])}</span>' if s["dur"] else ""
    desc = f'<div class="prose">{paras(s["desc"])}</div>' if s["desc"] else ""
    drill = (f'<div class="drill"><p class="drill-h">{esc(_L["drill"])}</p><p>{esc(s["drill"])}</p></div>'
             if s["drill"] else "")
    if custom:
        check_label = 'aria-label="Mark this milestone done"'
        title = (f'<input type="text" class="custom-title" data-f="{key}-title" maxlength="{MAX_LABEL}" '
                 'aria-label="Milestone name" placeholder="Name your milestone">')
        yours = " (yours)"
        remove = '<button type="button" class="ghost rm" data-remove>Remove</button>'
        cls = "step custom"
    else:
        check_label = ""
        title = f'<label class="step-title" for="chk-{key}">{esc(s["title"])}</label>'
        yours, remove, cls = "", "", "step"
    plan = (
        '<div class="step-plan">'
        f'<label class="due-field" for="due-{key}"><span>Target date</span>'
        f'<input type="date" class="date" id="due-{key}" data-f="{key}-due"></label>{remove}</div>'
    )
    note = note_box(f"{key}-note", "Add a note", "Your notes for this item",
                    "What went well, what got in the way?")
    return (
        f'<li class="{cls}" data-key="{key}">'
        f'<input type="checkbox" class="chk" id="chk-{key}" data-f="{key}-done" {check_label} aria-describedby="sm-{key}">'
        f'<div class="step-body"><p class="step-meta" id="sm-{key}"><span>{esc(_L["step"])} <span class="num">{n}</span>{yours}</span>{dur}</p>'
        f'{title}{desc}{drill}{plan}{note}</div></li>'
    )


def render_action(ctx) -> str:
    rows = "".join(render_step(f"s{i}", i + 1, s) for i, s in enumerate(ctx["steps"]))
    blank = {"title": "", "desc": "", "dur": "", "drill": ""}
    template = render_step("__K__", 0, blank, custom=True)
    return (
        '<section class="panel" id="panel-action" role="tabpanel" aria-labelledby="tab-action" tabindex="0" hidden>'
        f'<div class="action-head"><h2>{esc(_L["action"])}</h2>'
        '<button type="button" class="ghost" id="reset">Uncheck all steps</button></div>'
        f'<ol class="steps" id="steps">{rows}</ol>'
        '<button type="button" class="add-step" id="add-step">Add your own milestone</button>'
        f'<template id="tpl-step">{template}</template></section>'
    )


def render_schedule(ctx) -> str:
    groups = []
    for gi, g in enumerate(ctx["schedule"]):
        rows = []
        for ii, it in enumerate(g["items"]):
            k = f"d{gi}-{ii}"
            time = f'<span class="s-time">{esc(it["time"])}</span>' if it["time"] else ""
            ver = '<span class="verify">Verify</span>' if it["verify"] else ""
            note = f'<p class="s-note">{esc(it["note"])}</p>' if it["note"] else ""
            rows.append(
                f'<li class="sitem"><input type="checkbox" class="sdone" id="chk-{k}" data-f="{k}-done">'
                f'<div class="sbody"><p class="s-head">{time}<label for="chk-{k}" class="s-title">{esc(it["title"])}</label>{ver}</p>'
                f'{note}{note_box(k + "-note", "Add a note", "Your note on " + it["title"])}</div></li>'
            )
        summ = f'<p class="g-sum">{esc(g["summary"])}</p>' if g["summary"] else ""
        groups.append(f'<section class="group"><h2>{esc(g["title"])}</h2>{summ}<ul class="slist">{"".join(rows)}</ul></section>')
    return ('<section class="panel" id="panel-schedule" role="tabpanel" aria-labelledby="tab-schedule" tabindex="0" hidden>'
            f'<h2 class="sr-only">{esc(_L["schedule"])}</h2>{"".join(groups)}</section>')


def render_checklist(ctx) -> str:
    groups = []
    for gi, g in enumerate(ctx["checklist"]):
        rows = "".join(
            f'<li class="citem"><input type="checkbox" class="cdone" id="chk-k{gi}-{ii}" data-f="k{gi}-{ii}-done">'
            f'<label for="chk-k{gi}-{ii}">{esc(t)}</label></li>' for ii, t in enumerate(g["items"]))
        groups.append(f'<section class="group"><h2>{esc(g["title"])}</h2><ul class="clist">{rows}</ul></section>')
    return ('<section class="panel" id="panel-checklist" role="tabpanel" aria-labelledby="tab-checklist" tabindex="0" hidden>'
            f'<h2 class="sr-only">{esc(_L["checklist"])}</h2>{"".join(groups)}</section>')


def render_budget(ctx) -> str:
    b = ctx["budget"]
    rows = []
    for i, it in enumerate(b["items"]):
        est = f'{it["est"]:,.2f}' if it["est"] is not None else "n/a"
        ver = ' <span class="verify">Verify</span>' if it["verify"] else ""
        data = f' data-est="{it["est"]}"' if it["est"] is not None else ""
        rows.append(
            f'<tr><th scope="row">{esc(it["label"])}{ver}</th><td{data}>{est}</td>'
            f'<td><input type="number" min="0" step="any" inputmode="decimal" class="num-in" data-f="b{i}-actual" '
            f'aria-label="Actual cost: {esc(it["label"])}"></td></tr>')
    return (
        '<section class="panel" id="panel-budget" role="tabpanel" aria-labelledby="tab-budget" tabindex="0" hidden>'
        f'<h2>{esc(_L["budget"])}</h2><div class="tablewrap"><table class="budget" id="budget" data-cur="{esc(b["cur"])}">'
        '<thead><tr><th scope="col">Item</th><th scope="col">Estimate</th><th scope="col">Actual</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '<tfoot><tr><th scope="row">Total</th><td id="b-est"></td><td id="b-act"></td></tr>'
        '<tr><th scope="row">Difference (entered items)</th><td></td><td id="b-diff"></td></tr></tfoot></table></div>'
        '<p class="g-sum">Estimates are planning figures. Confirm real prices before paying.</p></section>'
    )


def render_deadlines(ctx) -> str:
    rows = []
    for i, d in enumerate(ctx["deadlines"]):
        date = f'<span class="j-date" data-date="{esc(d["date"])}">{esc(d["date"]) or "No date"}</span>'
        note = f'<p class="s-note">{esc(d["note"])}</p>' if d["note"] else ""
        rows.append(
            f'<li class="sitem"><input type="checkbox" class="sdone" id="chk-x{i}" data-f="x{i}-done">'
            f'<div class="sbody"><p class="s-head">{date}<label for="chk-x{i}" class="s-title">{esc(d["title"])}</label></p>{note}</div></li>')
    return ('<section class="panel" id="panel-deadlines" role="tabpanel" aria-labelledby="tab-deadlines" tabindex="0" hidden>'
            f'<h2>{esc(_L["deadlines"])}</h2><ul class="slist">{"".join(rows)}</ul></section>')


_PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M8 5v14l11-7z"/></svg>'


def render_videos(videos) -> str:
    cards = []
    for idx, v in enumerate(videos):
        if v["vid"]:
            player = (
                f'<div class="player" data-vid="{esc(v["vid"])}" data-title="{esc(v["title"])}">'
                f'<button type="button" class="facade" aria-label="Play video: {esc(v["title"])}">'
                f'<img class="facade-img" src="https://i.ytimg.com/vi/{esc(v["vid"])}/hqdefault.jpg" alt="" loading="lazy">'
                f'<span class="play">{_PLAY}</span></button></div>'
            )
        else:
            player = ""
        meta = "".join(f"<span>{esc(x)}</span>" for x in (v["channel"], v["duration"]) if x)
        summary = f'<p class="vsummary">{esc(v["summary"])}</p>' if v["summary"] else ""
        take = ""
        if v["takeaways"]:
            take = ('<div class="tips"><p class="tips-h">Takeaways</p><ul>'
                    + "".join(f"<li>{esc(t)}</li>" for t in v["takeaways"]) + "</ul></div>")
        stamps = ""
        if v["stamps"]:
            lis = []
            for s in v["stamps"]:
                href = v["url"] + ("&" if "?" in v["url"] else "?") + f"t={s['secs']}s"
                lis.append(
                    f'<li><a class="ts" href="{esc(href)}" target="_blank" rel="noopener noreferrer" '
                    f'data-seek="{s["secs"]}"><span class="ts-time">{esc(s["time"])}</span>'
                    f'<span>{esc(s["label"])}</span></a></li>'
                )
            stamps = f'<ul class="stamps" aria-label="Jump to a moment">{"".join(lis)}</ul>'
        vnote = note_box(f"v{idx}-note", "Add notes or bookmarks", "Your notes on this video",
                         "e.g. 5:30, rewatch before practice")
        cards.append(
            f'<article class="video">{player}<div class="video-body">'
            f'<h3><a href="{esc(v["url"])}" target="_blank" rel="noopener noreferrer">{esc(v["title"])}</a></h3>'
            f'<p class="meta">{meta}</p>{summary}{take}{stamps}{vnote}</div></article>'
        )
    return f'<section aria-labelledby="v-h"><h2 id="v-h">Videos</h2><div class="videos">{"".join(cards)}</div></section>' if cards else ""


def render_resources(ctx) -> str:
    web = ""
    if ctx["web"]:
        lis = "".join(
            f'<li><a href="{esc(w["url"])}" target="_blank" rel="noopener noreferrer">'
            f'<span class="wl-title">{esc(w["title"])}</span><span class="wl-host">{esc(w["host"])}</span></a></li>'
            for w in ctx["web"]
        )
        web = f'<section aria-labelledby="w-h"><h2 id="w-h">Further reading</h2><ul class="weblinks">{lis}</ul></section>'
    return (
        '<section class="panel" id="panel-resources" role="tabpanel" aria-labelledby="tab-resources" tabindex="0" hidden>'
        f'{render_videos(ctx["videos"])}{web}</section>'
    )


def render_notes() -> str:
    """Static shell. The timeline and takeaways are rebuilt by JS from live DOM state."""
    return (
        '<section class="panel" id="panel-notes" role="tabpanel" aria-labelledby="tab-notes" tabindex="0" hidden>'
        '<h2>Notes and journal</h2><p class="j-summary" id="j-summary"></p>'
        '<section aria-labelledby="j1"><h3 class="j-h" id="j1">Timeline</h3><div id="j-timeline"></div></section>'
        '<section aria-labelledby="j2"><h3 class="j-h" id="j2">Your notes</h3><div id="j-takeaways"></div></section>'
        '<section aria-labelledby="j3"><h3 class="j-h" id="j3">Journal</h3>'
        '<label class="sr-only" for="journal">Freeform journal</label>'
        f'<textarea class="journal" id="journal" data-f="journal" maxlength="{MAX_NOTE * 4}" rows="10" '
        'placeholder="What worked, what to change next."></textarea></section></section>'
    )


# -- CSS / JS (plain strings: no format braces to escape) ---------------------

CSS = r"""
:root{
  color-scheme: light dark;
  --bg:hsl(var(--h),28%,97%); --surface:hsl(var(--h),30%,99%);
  --ink:hsl(var(--h),35%,11%); --muted:hsl(var(--h),14%,36%);
  --rule:hsl(var(--h),18%,84%); --accent:hsl(var(--h),72%,30%);
  --accent-bg:hsl(var(--h),55%,92%); --focus:hsl(var(--h),85%,40%);
  --serif:'Fraunces',Georgia,'Times New Roman',serif;
  --sans:'Instrument Sans',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  --measure:68ch;
}
@media (prefers-color-scheme:dark){:root{
  --bg:hsl(var(--h),22%,9%); --surface:hsl(var(--h),20%,12%);
  --ink:hsl(var(--h),25%,93%); --muted:hsl(var(--h),12%,70%);
  --rule:hsl(var(--h),14%,23%); --accent:hsl(var(--h),78%,72%);
  --accent-bg:hsl(var(--h),32%,18%); --focus:hsl(var(--h),90%,70%);
}}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:400 16px/1.65 var(--sans);-webkit-font-smoothing:antialiased}
h1,h2,h3,p,ul,ol,figure,blockquote{margin:0}
ul,ol{padding:0;list-style:none}
a{color:inherit}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px;border-radius:4px}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}

/* navigation */
.nav{position:sticky;top:0;z-index:10;background:var(--bg);border-bottom:1px solid var(--rule)}
.nav-in{max-width:860px;margin:0 auto;padding:0 20px;display:flex;align-items:center;gap:16px}
.tabs{display:flex;overflow-x:auto;scrollbar-width:none;flex:1}
.tabs::-webkit-scrollbar{display:none}
.tab{font:500 14px/1 var(--sans);color:var(--muted);background:none;border:0;border-bottom:2px solid transparent;
  padding:16px 14px;cursor:pointer;white-space:nowrap}
.tab:hover{color:var(--ink)}
.tab[aria-selected="true"]{color:var(--accent);border-bottom-color:var(--accent)}
.progress{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--muted);white-space:nowrap}
.track{width:72px;height:4px;border-radius:4px;background:var(--rule);overflow:hidden}
.bar{height:100%;width:0;background:var(--accent);transition:width .3s ease}

/* layout */
main{max-width:860px;margin:0 auto;padding:40px 20px 96px}
.panel[hidden]{display:none}
.panel:focus:not(:focus-visible){outline:none}
h2{font:700 1.375rem/1.3 var(--serif);margin-bottom:16px}
h3{font:700 1.125rem/1.35 var(--serif)}
.prose{max-width:var(--measure)}
.prose p+p{margin-top:.8em}

/* hero */
.hero{padding:24px 0 40px;border-bottom:1px solid var(--rule);margin-bottom:32px}
.level{display:inline-block;font-size:14px;font-weight:600;color:var(--accent);border-left:3px solid var(--accent);padding-left:10px;margin-bottom:20px}
h1{font:700 clamp(2.1rem,6vw,3.6rem)/1.1 var(--serif);letter-spacing:-.015em;max-width:18ch}
.goal{font-family:var(--serif);font-size:1.2rem;line-height:1.6;color:var(--muted);max-width:52ch;margin-top:20px}
.hero-quote{margin-top:32px}
.quote{border-left:3px solid var(--rule);padding:2px 0 2px 20px;max-width:56ch}
.quote blockquote p{font:italic 400 1.125rem/1.6 var(--serif)}
.quote figcaption{margin-top:8px;font-size:14px;color:var(--muted)}
.quote+.quote{margin-top:24px}

/* overview extras */
.jumps{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:40px}
.jump{font:500 15px/1 var(--sans);color:var(--ink);background:var(--surface);border:1px solid var(--rule);
  border-radius:8px;padding:14px 16px;cursor:pointer;min-height:44px}
.jump:hover{border-color:var(--accent)}
.jump strong{color:var(--accent);font-weight:700;margin-left:4px}
.preview li{padding:14px 0;border-top:1px solid var(--rule);max-width:var(--measure)}
.preview li:first-child{border-top:0}

/* lessons */
.lesson{padding:28px 0;border-top:1px solid var(--rule)}
.lesson:first-of-type{border-top:0;padding-top:0}
.source{font-size:14px;color:var(--muted);margin:4px 0 10px}
.lesson h3+.prose{margin-top:10px}
.tips{margin-top:16px;padding:14px 18px;background:var(--accent-bg);border-radius:8px;max-width:var(--measure)}
.tips-h,.drill-h{font-size:14px;font-weight:600;color:var(--accent);margin-bottom:6px}
.tips li{position:relative;padding-left:16px;font-size:15px}
.tips li+li{margin-top:4px}
.tips li::before{content:"";position:absolute;left:0;top:.7em;width:6px;height:2px;background:var(--accent)}
.quotes{margin-top:48px;padding-top:32px;border-top:1px solid var(--rule)}

/* action plan */
.action-head{display:flex;align-items:baseline;justify-content:space-between;gap:16px;margin-bottom:8px}
.ghost{font:500 14px/1 var(--sans);color:var(--muted);background:none;border:0;padding:8px;cursor:pointer;text-decoration:underline;text-underline-offset:3px}
.ghost:hover{color:var(--ink)}
.steps{counter-reset:none}
.step{display:flex;gap:16px;padding:22px 0;border-top:1px solid var(--rule)}
.step:first-child{border-top:0}
.chk{width:22px;height:22px;flex:none;margin-top:2px;accent-color:var(--accent);cursor:pointer}
.step-body{min-width:0}
.step-meta{display:flex;gap:12px;font-size:14px;color:var(--muted);margin-bottom:2px}
.step-meta span:first-child{font-weight:600;color:var(--accent)}
.step-title{display:block;font:700 1.125rem/1.4 var(--serif);cursor:pointer;margin-bottom:6px}
.step.done .step-title{text-decoration:line-through;text-decoration-thickness:1px;color:var(--muted)}
.drill{margin-top:12px;padding:12px 16px;border-left:3px solid var(--accent);background:var(--accent-bg);border-radius:0 8px 8px 0;max-width:var(--measure);font-size:15px}

/* resources */
.panel>section+section{margin-top:48px}
.videos{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:28px 24px}
.player{aspect-ratio:16/9;background:var(--rule);border-radius:10px;overflow:hidden}
.player iframe,.facade{width:100%;height:100%;border:0;display:block}
.facade{position:relative;padding:0;background:var(--rule);cursor:pointer}
.facade-img{width:100%;height:100%;object-fit:cover;display:block}
.play{position:absolute;inset:0;display:grid;place-items:center;background:rgba(0,0,0,.28)}
.play svg{width:52px;height:52px;fill:#fff;filter:drop-shadow(0 2px 8px rgba(0,0,0,.5))}
.video-body{padding-top:12px}
.video h3 a{text-decoration:none}
.video h3 a:hover{text-decoration:underline}
.meta{display:flex;gap:12px;font-size:14px;color:var(--muted);margin-top:2px}
.vsummary{font-size:15px;margin-top:10px}
.stamps{margin-top:12px;display:flex;flex-direction:column}
.ts{display:flex;gap:12px;padding:6px 0;font-size:14px;color:var(--muted);text-decoration:none}
.ts:hover{color:var(--ink)}
.ts-time{font-variant-numeric:tabular-nums;font-weight:600;color:var(--accent);min-width:3.5em}
.weblinks a{display:flex;justify-content:space-between;gap:16px;align-items:baseline;padding:14px 0;border-top:1px solid var(--rule);text-decoration:none;max-width:var(--measure)}
.weblinks li:first-child a{border-top:0}
.weblinks a:hover .wl-title{text-decoration:underline}
.wl-title{font-weight:500}
.wl-host{font-size:14px;color:var(--muted);flex:none}
.empty{color:var(--muted);padding:48px 0}

/* single load sequence: hero only */
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.hero>*{animation:rise .55s cubic-bezier(.2,.7,.2,1) both}
.hero>:nth-child(2){animation-delay:.08s}.hero>:nth-child(3){animation-delay:.16s}.hero>:nth-child(4){animation-delay:.28s}
@media (prefers-reduced-motion:reduce){.hero>*{animation:none}.bar{transition:none}}

@media (max-width:600px){
  main{padding-top:28px}
  .nav-in{padding:0 8px 0 12px;gap:8px}
  .track{display:none}
  .videos{grid-template-columns:1fr}
}
"""

CSS_EXTRA = r"""
:root{--field-bd:hsl(var(--h),12%,50%)}
@media (prefers-color-scheme:dark){:root{--field-bd:hsl(var(--h),10%,52%)}}

/* version line, finish line */
.hero-meta{display:flex;flex-wrap:wrap;align-items:center;gap:6px 16px;margin-bottom:20px}
.hero-meta .level{margin-bottom:0}
.ver{font-size:13px;color:var(--muted)}
.target{display:flex;flex-wrap:wrap;gap:14px 20px;margin-top:28px;max-width:600px}
.field{display:flex;flex-direction:column;gap:4px;font-size:14px;color:var(--muted);flex:1 1 220px}
.field:last-child{flex:0 1 200px}

/* shared controls */
.date,.text-in,.custom-title,.note-input,.journal,.num-in{font:inherit;color:var(--ink);background:var(--surface);
  border:1px solid var(--field-bd);border-radius:8px;padding:8px 10px;max-width:100%}
.date{font-size:15px}
.text-in{font-size:15px;width:100%}

/* in-place notes */
.note{margin-top:14px;max-width:var(--measure)}
.note summary{cursor:pointer;font-size:14px;font-weight:600;color:var(--accent);padding:4px 0;width:fit-content;
  min-height:44px;display:flex;align-items:center}
.note-input{display:block;width:100%;margin-top:8px;min-height:84px;resize:vertical;font-size:15px;line-height:1.55}

/* action plan additions */
.ghost{min-height:44px;display:inline-flex;align-items:center}
.step-plan{display:flex;flex-wrap:wrap;align-items:center;gap:8px 20px;margin-top:14px}
.due-field{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--muted)}
.rm{margin-left:auto}
.rm.armed{color:var(--accent);font-weight:600}
.custom-title{display:block;width:100%;font:700 1.125rem/1.4 var(--serif);margin-bottom:6px}
.add-step{font:600 15px/1 var(--sans);color:var(--accent);background:none;border:1px dashed var(--accent);
  border-radius:8px;padding:14px 18px;margin-top:12px;cursor:pointer;min-height:44px}
.add-step:hover{background:var(--accent-bg)}
.facade[hidden]{display:none}

/* tab badge */
.badge{display:inline-block;min-width:1.5em;margin-left:6px;padding:2px 6px;border-radius:99px;
  background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:700;line-height:1.3;text-align:center}
.badge[hidden]{display:none}

/* notes and journal */
.j-summary{color:var(--muted);margin:-8px 0 36px}
.j-h{font:700 1.125rem/1.35 var(--serif);margin-bottom:12px}
.timeline>li,.takeaways>li{padding:16px 0;border-top:1px solid var(--rule)}
.timeline>li:first-child,.takeaways>li:first-child{border-top:0}
.j-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 12px;margin-bottom:8px}
.j-date{font-weight:600;color:var(--accent);min-width:6em}
.chip{font-size:13px;font-weight:600;color:var(--muted)}
.chip.done{color:var(--accent)}
.j-note{max-width:var(--measure)}
.j-note .note-input{margin-top:0}
.journal{width:100%;max-width:var(--measure);min-height:220px;resize:vertical;font:400 1rem/1.7 var(--serif)}

/* notice and assumptions */
.notice{margin:0 0 32px;padding:14px 18px;border:1px solid var(--accent);border-left-width:4px;
  background:var(--accent-bg);border-radius:8px;max-width:var(--measure);font-size:15px}
.assume{margin-bottom:40px}
.assume li{position:relative;padding:4px 0 4px 16px;font-size:15px}
.assume li::before{content:"";position:absolute;left:0;top:.95em;width:6px;height:2px;background:var(--accent)}

/* schedule, checklist, deadlines */
.g-sum{color:var(--muted);font-size:15px;margin:-6px 0 12px;max-width:var(--measure)}
.sitem,.citem{display:flex;gap:14px;padding:14px 0;border-top:1px solid var(--rule)}
.slist>.sitem:first-child,.clist>.citem:first-child{border-top:0}
.sdone,.cdone{width:22px;height:22px;flex:none;margin-top:2px;accent-color:var(--accent);cursor:pointer}
.sbody{min-width:0}
.s-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 12px}
.s-time{font-weight:600;color:var(--accent);font-variant-numeric:tabular-nums}
.s-title{font-weight:600;cursor:pointer}
.s-note{font-size:15px;color:var(--muted);margin-top:4px;max-width:var(--measure)}
.sdone:checked+.sbody .s-title{text-decoration:line-through;color:var(--muted)}
.cdone:checked+label{text-decoration:line-through;color:var(--muted)}
.citem label{cursor:pointer}
.verify{font-size:12px;font-weight:700;color:var(--accent);border:1px solid var(--accent);border-radius:99px;padding:1px 8px}

/* budget */
.tablewrap{overflow-x:auto}
.budget{border-collapse:collapse;width:100%;max-width:var(--measure);font-size:15px}
.budget th,.budget td{text-align:left;padding:10px 8px;border-top:1px solid var(--rule)}
.budget thead th{font-size:14px;color:var(--muted);border-top:0}
.budget tfoot{font-weight:700}
.num-in{width:8em}

/* save bar */
.savebar{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:20;display:flex;align-items:center;
  gap:16px;max-width:calc(100% - 24px);padding:10px 12px 10px 18px;background:var(--ink);color:var(--bg);
  border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.28);font-size:14px;animation:barIn .22s ease both}
.savebar[hidden]{display:none}
.savebar :focus-visible{outline-color:var(--bg)}
.savebtn{font:600 14px/1 var(--sans);color:var(--ink);background:var(--bg);border:0;border-radius:8px;padding:12px 14px;cursor:pointer;min-height:44px}
.savebtn:disabled{opacity:.6;cursor:default}
@keyframes barIn{from{opacity:0;transform:translate(-50%,8px)}to{opacity:1;transform:translate(-50%,0)}}
@media (prefers-reduced-motion:reduce){.savebar{animation:none}}
@media (max-width:600px){
  .savebar{left:12px;right:12px;transform:none;flex-wrap:wrap;justify-content:space-between;animation:none}
  .step-plan{align-items:flex-start}
}

/* print: show every panel, drop chrome */
@media print{
  .nav,.savebar{display:none}
  .panel[hidden]{display:block}
  .panel{break-before:page}
  .panel:first-of-type{break-before:auto}
  main{padding:0}
  .hero>*{animation:none}
}
"""
CSS = CSS + CSS_EXTRA

JS = r"""
(function () {
  'use strict';
  var TARGET = __TARGET_ORIGIN__, MSG = __MSG_TYPE__;
  var app = document.getElementById('app');
  var BASE = 'mentor-guide:' + app.getAttribute('data-key');
  var STEP = app.getAttribute('data-step') || 'Step';
  var version = parseInt(app.getAttribute('data-version'), 10) || 1;
  var CUSTOM_KEY = /^c\d{1,4}$/;
  var baseline = {}, baseCustom = [], mem = null, persistTimer = null, flashUntil = 0, flashTimer = null;

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function dkey() { return BASE + ':v' + version; }
  function plural(n, one, many) { return n + ' ' + (n === 1 ? one : many); }
  function verText(v) { return 'Version ' + v + (v === 1 ? ', AI original' : ', augmented by you'); }
  function clipText(s, n) { s = (s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '\u2026' : s; }

  /* ---- field access: every editable control has a data-f key ---- */
  function fields() { return $$('[data-f]'); }
  function byKey(k) { var a = fields(); for (var i = 0; i < a.length; i++) if (a[i].getAttribute('data-f') === k) return a[i]; return null; }
  function getVal(el) { return el.type === 'checkbox' ? el.checked : el.value; }
  function setVal(el, v) { if (el.type === 'checkbox') el.checked = !!v; else el.value = v == null ? '' : String(v); }
  function collect() { var o = {}; fields().forEach(function (el) { o[el.getAttribute('data-f')] = getVal(el); }); return o; }
  function customKeys() { return $$('.step.custom').map(function (r) { return r.getAttribute('data-key'); }); }
  function norm(v) { return v === undefined || v === null || v === false ? '' : v; }

  /* ---- custom milestones ---- */
  var tpl = document.getElementById('tpl-step'), list = document.getElementById('steps'), nextId = 1;
  function bumpNext(k) { var n = parseInt(k.slice(1), 10); if (n >= nextId) nextId = n + 1; }
  customKeys().forEach(bumpNext);
  function addCustom(key) {
    if (!tpl || !list) return null;
    if (!key) key = 'c' + nextId;
    if (!CUSTOM_KEY.test(key)) return null;
    bumpNext(key);
    var holder = document.createElement('div');
    holder.innerHTML = tpl.innerHTML.replace(/__K__/g, key);
    var row = holder.firstElementChild;
    list.appendChild(row);
    return row;
  }
  function renumber() { $$('.step').forEach(function (r, i) { var n = $('.num', r); if (n) n.textContent = String(i + 1); }); }

  /* ---- derived UI ---- */
  function syncNotes(open) {
    $$('details.note').forEach(function (d) {
      var t = $('textarea', d), s = $('summary', d);
      if (!t || !s) return;
      var has = t.value.trim() !== '';
      s.textContent = s.getAttribute(has ? 'data-filled' : 'data-empty');
      if (open && has) d.open = true;
    });
  }
  function counts() {
    var notes = 0, dates = 0;
    $$('textarea[data-f]').forEach(function (t) { if (t.value.trim()) notes++; });
    $$('input[type="date"][data-f]').forEach(function (i) { if (i.value) dates++; });
    return { notes: notes, dates: dates, custom: customKeys().length };
  }
  function renderProgress() {
    var boxes = $$('.chk, .sdone, .cdone'), done = 0;
    boxes.forEach(function (b) {
      if (b.checked) done++;
      var r = b.closest('.step'); if (r) r.classList.toggle('done', b.checked);
    });
    var total = boxes.length, pct = total ? Math.round(done / total * 100) : 0;
    var bar = $('#bar'), label = $('#prog-text'), meter = $('#meter');
    if (bar) bar.style.width = pct + '%';
    if (meter) meter.setAttribute('aria-valuenow', String(pct));
    if (label) label.textContent = !total ? 'Nothing to track yet' : done === total ? 'All ' + total + ' done' : done + ' of ' + total + ' done';
  }
  function renderBudget() {
    var t = $('#budget'); if (!t) return;
    var cur = t.getAttribute('data-cur') || '', est = 0, act = 0, estEntered = 0, any = false;
    $$('[data-est]', t).forEach(function (e) { est += parseFloat(e.getAttribute('data-est')) || 0; });
    $$('tbody tr', t).forEach(function (r) {
      var i = $('input', r), e = $('[data-est]', r), v = i ? parseFloat(i.value) : NaN;
      if (!isNaN(v)) { act += v; any = true; if (e) estEntered += parseFloat(e.getAttribute('data-est')) || 0; }
    });
    function f(n) { return (cur ? cur + ' ' : '') + n.toLocaleString(undefined, { maximumFractionDigits: 2 }); }
    var be = $('#b-est'), ba = $('#b-act'), bd = $('#b-diff');
    if (be) be.textContent = f(est);
    if (ba) ba.textContent = any ? f(act) : '\u2013';
    if (bd) bd.textContent = any ? (act - estEntered >= 0 ? '+' : '') + f(act - estEntered) : '';
  }
  function renderBadge() {
    var b = $('#note-count'), n = counts().notes;
    if (b) { b.textContent = String(n); b.hidden = n === 0; }
  }
  function renderSummary() {
    var s = $('#j-summary'); if (!s) return;
    var c = counts();
    s.textContent = plural(c.notes, 'note', 'notes') + ' captured, ' + plural(c.dates, 'target date', 'target dates') +
      ' scheduled, ' + plural(c.custom, 'custom step', 'custom steps') + '.';
  }

  /* ---- dirty tracking against the last saved/baked state ---- */
  function dirtyCount() {
    var cur = collect(), cc = customKeys(), n = 0, k;
    var added = cc.filter(function (c) { return baseCustom.indexOf(c) < 0; });
    var removed = baseCustom.filter(function (c) { return cc.indexOf(c) < 0; });
    function skip(key) { var p = key.split('-')[0]; return added.indexOf(p) > -1 || removed.indexOf(p) > -1; }
    for (k in cur) if (!skip(k) && norm(cur[k]) !== norm(baseline[k])) n++;
    for (k in baseline) if (!(k in cur) && !skip(k) && norm(baseline[k]) !== '') n++;
    return n + added.length + removed.length;
  }
  function refreshBar() {
    var bar = $('#savebar'); if (!bar) return;
    var n = dirtyCount(), flashing = Date.now() < flashUntil;
    bar.hidden = !(n > 0 || flashing);
    $('#bar-msg').textContent = n > 0 ? verText(version) + ', ' + plural(n, 'unsaved change', 'unsaved changes')
                                      : 'Saved. ' + verText(version);
    $('#save').disabled = n === 0;
  }

  /* ---- draft autosave (per guide and version) ---- */
  function persist() {
    clearTimeout(persistTimer);
    persistTimer = setTimeout(function () {
      var d = { fields: collect(), custom: customKeys() };
      mem = d;
      try {
        if (dirtyCount() === 0) localStorage.removeItem(dkey());
        else localStorage.setItem(dkey(), JSON.stringify(d));
      } catch (e) {}
    }, 250);
  }
  function loadDraft() {
    try { var s = localStorage.getItem(dkey()); if (s) { var d = JSON.parse(s); if (d && typeof d === 'object') return d; } } catch (e) {}
    return mem;
  }
  function restore(d) {
    if (!d || typeof d.fields !== 'object' || !d.fields) return;
    var want = (Array.isArray(d.custom) ? d.custom : []).filter(function (k) { return typeof k === 'string' && CUSTOM_KEY.test(k); });
    customKeys().forEach(function (k) {
      if (want.indexOf(k) < 0) { var r = $('.step[data-key="' + k + '"]'); if (r) r.remove(); }
    });
    want.forEach(function (k) { if (customKeys().indexOf(k) < 0) addCustom(k); });
    fields().forEach(function (el) {
      var k = el.getAttribute('data-f');
      if (Object.prototype.hasOwnProperty.call(d.fields, k)) setVal(el, d.fields[k]);
    });
  }

  function onEdit() { renderBudget(); syncNotes(false); renderProgress(); renderBadge(); renderSummary(); refreshBar(); }

  /* ---- notes and journal tab: rebuilt from the DOM, so it cannot drift ---- */
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function fmtDate(v) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v || ''); if (!m) return '';
    var d = new Date(+m[1], +m[2] - 1, +m[3]), opt = { month: 'short', day: 'numeric' };
    if (d.getFullYear() !== new Date().getFullYear()) opt.year = 'numeric';
    return d.toLocaleDateString(undefined, opt);
  }
  function mirror(key, label) {
    var src = byKey(key), t = el('textarea', 'note-input');
    t.value = src ? src.value : '';
    t.setAttribute('data-mirror', key);
    t.setAttribute('maxlength', '4000');
    t.setAttribute('rows', '3');
    t.setAttribute('aria-label', label);
    return t;
  }
  function empty(text) { return el('p', 'empty', text); }

  function buildJournal() {
    var tl = $('#j-timeline'), tk = $('#j-takeaways');
    if (!tl || !tk) return;
    tl.textContent = ''; tk.textContent = '';

    var items = [], tv = byKey('target'), tt = byKey('target-text');
    if ((tv && tv.value) || (tt && tt.value.trim())) {
      items.push({ date: tv ? tv.value : '', title: 'Finish line' + (tt && tt.value.trim() ? ': ' + tt.value.trim() : ''), order: -1, plain: true });
    }
    $$('.step').forEach(function (r, i) {
      var k = r.getAttribute('data-key'), due = byKey(k + '-due'), note = byKey(k + '-note'), done = byKey(k + '-done');
      var dv = due ? due.value : '', nv = note ? note.value.trim() : '';
      if (!dv && !nv) return;
      var ct = $('.custom-title', r), name = ct ? (ct.value.trim() || 'Untitled milestone') : ($('.step-title', r) || {}).textContent;
      items.push({ date: dv, title: STEP + ' ' + (i + 1) + ': ' + name, done: !!(done && done.checked), key: k + '-note', order: i });
    });
    $$('#panel-deadlines .sitem').forEach(function (r, i) {
      var d = $('.j-date', r), dv = d ? d.getAttribute('data-date') : '';
      if (!dv) return;
      var t = $('.s-title', r), cb = $('input[type="checkbox"]', r);
      items.push({ date: dv, title: 'Deadline: ' + (t ? t.textContent : ''), done: !!(cb && cb.checked), order: 1000 + i });
    });
    items.sort(function (a, b) {
      if (a.date && b.date && a.date !== b.date) return a.date < b.date ? -1 : 1;
      if (a.date && !b.date) return -1;
      if (!a.date && b.date) return 1;
      return a.order - b.order;
    });
    if (!items.length) tl.appendChild(empty('Items with a target date or a note show up here. Set a date in the plan or deadlines.'));
    else {
      var ol = el('ol', 'timeline');
      items.forEach(function (it) {
        var li = el('li'), head = el('p', 'j-head');
        head.appendChild(el('span', 'j-date', it.date ? fmtDate(it.date) : 'No date'));
        head.appendChild(el('strong', null, it.title));
        if (!it.plain) head.appendChild(el('span', 'chip' + (it.done ? ' done' : ''), it.done ? 'Done' : 'To do'));
        li.appendChild(head);
        if (it.key) { var w = el('div', 'j-note'); w.appendChild(mirror(it.key, 'Your note for ' + it.title)); li.appendChild(w); }
        ol.appendChild(li);
      });
      tl.appendChild(ol);
    }

    var rows = [];
    $$('.lesson').forEach(function (a) {
      var t = $('textarea[data-f]', a); if (!t || !t.value.trim()) return;
      var h = $('h3', a), p = $('.prose p', a);
      rows.push({ label: 'Lesson: ' + (h ? h.textContent : clipText(p ? p.textContent : '', 60)), key: t.getAttribute('data-f') });
    });
    $$('#panel-schedule .sitem').forEach(function (a) {
      var t = $('textarea[data-f]', a); if (!t || !t.value.trim()) return;
      var h = $('.s-title', a);
      rows.push({ label: 'Plan: ' + (h ? h.textContent : 'Item'), key: t.getAttribute('data-f') });
    });
    $$('.video').forEach(function (a) {
      var t = $('textarea[data-f]', a); if (!t || !t.value.trim()) return;
      var h = $('h3', a);
      rows.push({ label: 'Video: ' + (h ? h.textContent : 'Untitled'), key: t.getAttribute('data-f') });
    });
    if (!rows.length) tk.appendChild(empty('Notes you add to lessons, schedule items and videos show up here.'));
    else {
      var ul = el('ul', 'takeaways');
      rows.forEach(function (r) {
        var li = el('li'), head = el('p', 'j-head');
        head.appendChild(el('strong', null, r.label));
        li.appendChild(head);
        var w = el('div', 'j-note'); w.appendChild(mirror(r.key, 'Your note on ' + r.label)); li.appendChild(w);
        ul.appendChild(li);
      });
      tk.appendChild(ul);
    }
    renderSummary();
  }

  /* ---- tabs (WAI-ARIA tabs pattern, roving tabindex) ---- */
  var tabs = $$('[role="tab"]');
  function show(name, focus) {
    tabs.forEach(function (t) {
      var on = t.getAttribute('data-panel') === name;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      var p = document.getElementById('panel-' + t.getAttribute('data-panel'));
      if (p) p.hidden = !on;
      if (on) {
        var strip = t.parentNode;   /* scroll the tab strip only, never the page */
        if (strip && strip.scrollWidth > strip.clientWidth) strip.scrollLeft = t.offsetLeft - (strip.clientWidth - t.offsetWidth) / 2;
        if (focus) t.focus();
      }
    });
    if (name === 'notes') buildJournal();
    try { history.replaceState(null, '', '#' + name); } catch (e) {}
    window.scrollTo(0, 0);
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { show(t.getAttribute('data-panel')); });
    t.addEventListener('keydown', function (ev) {
      var n = null;
      if (ev.key === 'ArrowRight') n = (i + 1) % tabs.length;
      else if (ev.key === 'ArrowLeft') n = (i - 1 + tabs.length) % tabs.length;
      else if (ev.key === 'Home') n = 0;
      else if (ev.key === 'End') n = tabs.length - 1;
      if (n !== null) { ev.preventDefault(); show(tabs[n].getAttribute('data-panel'), true); }
    });
  });

  /* ---- video: facade, then iframe; timestamps restart the iframe at `start` ---- */
  function play(player, secs) {
    var id = player.getAttribute('data-vid');
    var f = $('iframe', player) || document.createElement('iframe');
    f.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) +
      '?autoplay=1&rel=0&modestbranding=1&start=' + (secs || 0);
    f.title = player.getAttribute('data-title') || 'Video';
    f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    f.setAttribute('allowfullscreen', '');
    f.referrerPolicy = 'strict-origin-when-cross-origin';
    var face = $('.facade', player); if (face) face.hidden = true;
    if (!f.parentNode) player.appendChild(f);
  }

  /* ---- save: bake DOM state into a clone, hand it to the host ---- */
  function bake(nextVersion) {
    var live = $$('input, textarea'), root = document.documentElement.cloneNode(true);
    var cl = Array.prototype.slice.call(root.querySelectorAll('input, textarea'));
    live.forEach(function (src, i) {
      var c = cl[i]; if (!c) return;
      if (src.tagName === 'TEXTAREA') c.textContent = '\n' + src.value;  /* parser drops one leading newline */
      else if (src.type === 'checkbox') { if (src.checked) c.setAttribute('checked', 'checked'); else c.removeAttribute('checked'); }
      else c.setAttribute('value', src.value);
    });
    var ld = $$('details.note'), cd = Array.prototype.slice.call(root.querySelectorAll('details.note'));
    ld.forEach(function (d, i) { if (cd[i]) { if (d.open) cd[i].setAttribute('open', ''); else cd[i].removeAttribute('open'); } });
    ['j-timeline', 'j-takeaways'].forEach(function (id) { var n = root.querySelector('#' + id); if (n) n.textContent = ''; });
    Array.prototype.forEach.call(root.querySelectorAll('.player'), function (p) {
      var f = p.querySelector('iframe'); if (f) f.parentNode.removeChild(f);
      var fc = p.querySelector('.facade'); if (fc) fc.removeAttribute('hidden');
    });
    var a = root.querySelector('#app'); if (a) a.setAttribute('data-version', String(nextVersion));
    var v = root.querySelector('#ver'); if (v) v.textContent = verText(nextVersion);
    var sb = root.querySelector('#savebar'); if (sb) sb.setAttribute('hidden', '');
    return '<!DOCTYPE html>\n' + root.outerHTML;
  }
  function download(html, v) {
    var u = URL.createObjectURL(new Blob([html], { type: 'text/html' })), a = document.createElement('a');
    a.href = u; a.download = 'mentor-guide-v' + v + '.html';
    document.body.appendChild(a); a.click(); a.parentNode.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(u); }, 1000);
  }
  function save() {
    if (dirtyCount() === 0) return;
    var next = version + 1, c = counts(), boxes = $$('.chk');
    var stats = { notesCount: c.notes, completedSteps: boxes.filter(function (b) { return b.checked; }).length,
                  totalSteps: boxes.length, targetDates: c.dates, customSteps: c.custom, version: next };
    var html = bake(next);
    if (window.parent && window.parent !== window) window.parent.postMessage({ type: MSG, payload: { html: html, stats: stats } }, TARGET);
    else download(html, next);
    version = next;
    app.setAttribute('data-version', String(version));
    var v = $('#ver'); if (v) v.textContent = verText(version);
    baseline = collect(); baseCustom = customKeys();
    flashUntil = Date.now() + 4000;
    clearTimeout(flashTimer); flashTimer = setTimeout(refreshBar, 4100);
    var live = $('#save-live'); if (live) live.textContent = 'Guide saved as version ' + version;
    refreshBar();
  }

  /* ---- events (delegated; nothing inline) ---- */
  function handleEdit(ev) {
    var t = ev.target; if (!t || !t.hasAttribute) return;
    if (t.hasAttribute('data-mirror')) { var c = byKey(t.getAttribute('data-mirror')); if (c) c.value = t.value; }
    else if (!t.hasAttribute('data-f')) return;
    onEdit(); persist();
  }
  document.addEventListener('input', handleEdit);
  document.addEventListener('change', handleEdit);
  document.addEventListener('click', function (ev) {
    var t = ev.target; if (!t.closest) return;
    var go = t.closest('[data-goto]'), seek = t.closest('[data-seek]'), face = t.closest('.facade'), rm = t.closest('[data-remove]');
    if (go) { show(go.getAttribute('data-goto')); }
    else if (seek) {
      var card = seek.closest('.video'), p = card && card.querySelector('.player');
      if (p) { ev.preventDefault(); play(p, parseInt(seek.getAttribute('data-seek'), 10) || 0); p.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
    } else if (face) { play(face.parentNode, 0); }
    else if (rm) {
      var row = rm.closest('.step');
      var filled = $$('[data-f]', row).some(function (e) { return e.type !== 'checkbox' && e.value.trim() !== ''; });
      if (filled && !rm.classList.contains('armed')) {
        rm.classList.add('armed'); rm.textContent = 'Confirm remove';
        setTimeout(function () { rm.classList.remove('armed'); rm.textContent = 'Remove'; }, 3500);
        return;
      }
      row.parentNode.removeChild(row); renumber(); onEdit(); persist();
      var add = $('#add-step'); if (add) add.focus();
    } else if (t.closest('#add-step')) {
      var r = addCustom(); if (r) { renumber(); var ti = $('.custom-title', r); if (ti) ti.focus(); onEdit(); persist(); }
    } else if (t.closest('#reset')) {
      $$('.chk').forEach(function (b) { b.checked = false; }); onEdit(); persist();
    } else if (t.closest('#save')) { save(); }
  });
  document.addEventListener('error', function (ev) {
    if (ev.target && ev.target.classList && ev.target.classList.contains('facade-img')) ev.target.style.display = 'none';
  }, true);

  /* ---- init: baked DOM is the baseline; a same-version draft layers on top ---- */
  baseline = collect(); baseCustom = customKeys();
  restore(loadDraft());
  renumber(); syncNotes(true);
  var v0 = $('#ver'); if (v0) v0.textContent = verText(version);
  onEdit();
  var start = (location.hash || '').slice(1);
  var names = tabs.map(function (t) { return t.getAttribute('data-panel'); });
  show(names.indexOf(start) > -1 ? start : names[0]);
})();
"""

CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src https://i.ytimg.com data:; "
       "frame-src https://www.youtube-nocookie.com; base-uri 'none'; form-action 'none'")

FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,700;1,9..144,400'
    '&family=Instrument+Sans:wght@400;500;600;700&display=swap">'
)


# -- Assembly -----------------------------------------------------------------

def wrap(doc: str) -> str:
    return f"<!-- synaptix-html-app -->{doc}<!-- /synaptix-html-app -->"


def error_page(message: str) -> str:
    return wrap(
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Guide unavailable</title>'
        '<style>body{font:16px/1.6 system-ui,sans-serif;max-width:520px;margin:15vh auto;padding:0 20px}</style></head>'
        f'<body><h1>The guide could not be built</h1><p>{esc(message)}</p></body></html>'
    )


def _js_str(value: str) -> str:
    """JS string literal that cannot close a <script> block."""
    return json.dumps(value).replace("<", "\\u003c")


def build(inputs: dict, warnings: list) -> str:
    def warn(msg):
        if len(warnings) < 25:
            warnings.append(msg)

    topic = txt(inputs.get("topic"), MAX_TITLE) or "Your topic"
    if topic == "Your topic" and not inputs.get("topic"):
        warn("topic was missing; a placeholder title was used")
    depth_raw = txt(inputs.get("depth"), 30).lower()
    level = DEPTHS.get(depth_raw, "")
    if depth_raw and not level:
        warn(f"unknown depth '{depth_raw}'; expected beginner, intermediate or advanced")

    # Labels first: normalizers and renderers read them via _L.
    bp = norm_blueprint(inputs, warn)
    _L.clear()
    _L.update(bp["labels"])

    ctx = {
        "topic": topic,
        "goal": txt(inputs.get("goal"), 500),
        "level": level,
        "bp": bp,
        "lessons": norm_lessons(inputs.get("key_lessons"), warn),
        "quotes": norm_quotes(inputs.get("expert_quotes"), warn),
        "steps": norm_steps(inputs.get("action_steps"), warn),
        "videos": norm_videos(inputs.get("videos"), warn),
        "web": norm_web(inputs.get("web_sources"), warn),
        "schedule": norm_schedule(inputs.get("schedule"), warn),
        "checklist": norm_checklist(inputs.get("checklist"), warn),
        "budget": norm_budget(inputs.get("budget"), warn),
        "deadlines": norm_deadlines(inputs.get("deadlines"), warn),
    }

    key = hashlib.sha256(("\x1f".join([topic] + [s["title"] for s in ctx["steps"]])).encode("utf-8")).hexdigest()[:16]

    # Action plan and notes always exist: users can add milestones and journal
    # even when the research returned no steps.
    tabs = [("overview", esc(_L["overview"]), render_overview(ctx))]
    if ctx["lessons"] or ctx["quotes"]:
        tabs.append(("lessons", esc(_L["lessons"]), render_lessons(ctx)))
    if ctx["schedule"]:
        tabs.append(("schedule", esc(_L["schedule"]), render_schedule(ctx)))
    tabs.append(("action", esc(_L["action"]), render_action(ctx)))
    if ctx["checklist"]:
        tabs.append(("checklist", esc(_L["checklist"]), render_checklist(ctx)))
    if ctx["budget"]:
        tabs.append(("budget", esc(_L["budget"]), render_budget(ctx)))
    if ctx["deadlines"]:
        tabs.append(("deadlines", esc(_L["deadlines"]), render_deadlines(ctx)))
    tabs.append(("notes", "Notes &amp; journal", render_notes()))
    if ctx["videos"] or ctx["web"]:
        tabs.append(("resources", "Resources", render_resources(ctx)))
    if not (ctx["lessons"] or ctx["quotes"] or ctx["steps"] or ctx["videos"] or ctx["web"]
            or ctx["schedule"] or ctx["checklist"] or ctx["budget"] or ctx["deadlines"]):
        warn("no lessons, steps, schedule or resources were provided; the guide starts empty")

    tab_html = "".join(
        f'<button type="button" class="tab" role="tab" id="tab-{n}" data-panel="{n}" '
        f'aria-controls="panel-{n}" aria-selected="{"true" if i == 0 else "false"}" '
        f'tabindex="{0 if i == 0 else -1}">{label}'
        + ('<span class="badge" id="note-count" hidden>0</span>' if n == "notes" else "")
        + "</button>"
        for i, (n, label, _) in enumerate(tabs)
    )
    n_track = (len(ctx["steps"]) + sum(len(g["items"]) for g in ctx["schedule"])
               + sum(len(g["items"]) for g in ctx["checklist"]) + len(ctx["deadlines"]))
    progress = (
        '<div class="progress"><div class="track" id="meter" role="progressbar" aria-label="Plan progress" '
        'aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="bar" id="bar"></div></div>'
        f'<span id="prog-text">{f"0 of {n_track} done" if n_track else "Nothing to track yet"}</span></div>'
    )
    savebar = (
        '<div class="savebar" id="savebar" role="region" aria-label="Save your changes" hidden>'
        '<span id="bar-msg"></span>'
        '<button type="button" class="savebtn" id="save">Save augmented guide</button></div>'
        '<p class="sr-only" id="save-live" aria-live="polite"></p>'
    )

    script = JS.replace("__TARGET_ORIGIN__", _js_str(SAVE_TARGET_ORIGIN)).replace("__MSG_TYPE__", _js_str(SAVE_MESSAGE_TYPE))
    fonts = FONT_LINKS if WEB_FONTS else ""
    csp = CSP if WEB_FONTS else CSP.replace(" https://fonts.googleapis.com", "").replace("font-src https://fonts.gstatic.com; ", "")
    desc = esc(clip(ctx["goal"] or f"Interactive guide for {topic}", 160))

    doc = (
        f'<!DOCTYPE html><html lang="{esc(bp["lang"])}" style="--h:{topic_hue(topic)}"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{esc(csp)}">'
        f'<meta name="description" content="{desc}"><meta name="color-scheme" content="light dark">'
        f'<title>{esc(topic)}: guide</title>{fonts}<style>{CSS}</style></head>'
        f'<body><div id="app" data-key="{key}" data-version="1" data-step="{esc(_L["step"])}">'
        f'<nav class="nav" aria-label="Guide sections"><div class="nav-in"><div class="tabs" role="tablist">{tab_html}</div>{progress}</div></nav>'
        f'<main>{"".join(p for _, _, p in tabs)}</main>{savebar}</div>'
        f'<script>{script}</script></body></html>'
    )
    return wrap(doc)


def run(raw_inputs) -> dict:
    warnings: list = []
    try:
        data = raw_inputs
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, dict):
            raise TypeError("inputs must be an object")
        html_app = build(data, warnings)
        summary = "Guide app built successfully"
        if warnings:
            summary += f" with {len(warnings)} input warning(s)"
        return {"html_app": html_app, "summary": summary, "warnings": warnings}
    except Exception as exc:  # last-resort guard: always return a renderable page
        return {
            "html_app": error_page(f"{type(exc).__name__}: {exc}"),
            "summary": f"Guide build failed: {type(exc).__name__}",
            "warnings": warnings + [str(exc)],
        }


# -- Self-test (python build_app.py) ------------------------------------------

def _check_keys(h: str) -> None:
    live_part = h.split('<template id="tpl-step">')[0] + h.split("</template>")[1]
    keys = re.findall(r'data-f="([^"]+)"', live_part)
    assert len(keys) == len(set(keys)), "data-f keys must be unique outside the template"
    ids = re.findall(r'\sid="([^"]+)"', live_part)
    assert len(ids) == len(set(ids)), "element ids must be unique"


def _selftest() -> None:
    hostile = {
        "topic": '<img src=x onerror=alert(1)> Guitar',
        "depth": "wizard",
        "key_lessons": ["plain string lesson", {"title": "<b>x</b>", "desc": "d", "tips": "- one\n- two"}, 42, None],
        "expert_quotes": ["just text", {"text": "q", "author": "A"}, {"author": "no text"},
                          {"text": " ".join(["w"] * 40), "author": "too long"}],
        "action_steps": ["do a thing", {"title": "t", "duration": "5 min"}],
        "videos": [
            {"url": "javascript:alert(1)", "title": "bad"},
            {"url": "https://youtu.be/dQw4w9WgXcQ", "title": "ok", "key_timestamps": ["1:05 intro", {"time": "x", "label": "bad"}]},
            "not a dict",
        ],
        "web_sources": [{"results": [{"title": "T", "url": "https://example.com/a"}, {"url": "data:text/html,x"}]}],
    }
    out = run(hostile)
    h = out["html_app"]
    assert h.startswith("<!-- synaptix-html-app -->") and h.endswith("<!-- /synaptix-html-app -->")
    assert "<img src=x" not in h and "javascript:alert" not in h and "data:text/html" not in h
    assert 'data-seek="65"' in h and 'data-vid="dQw4w9WgXcQ"' in h
    assert out["warnings"], "expected warnings for bad input"
    assert any("longer than" in w for w in out["warnings"]), "long quote should warn"
    assert "too long" not in h
    assert "failed" not in out["summary"]
    for bad in (None, [], "not json", {}):
        assert run(bad)["html_app"], "must always return a page"

    # v5 surface still intact
    for needle in ('data-f="s0-done"', 'data-f="s1-note"', 'data-f="l0-note"', 'data-f="v0-note"',
                   'data-f="target"', 'data-f="journal"', 'id="tpl-step"', 'id="panel-notes"', 'id="savebar"'):
        assert needle in h, f"missing {needle}"
    _check_keys(h)
    live_part = h.split('<template id="tpl-step">')[0] + h.split("</template>")[1]
    markup = re.sub(r"<script>.*?</script>", "", live_part, flags=re.S)  # the JS legitimately contains /__K__/g
    assert "__K__" in h.split("<template")[1].split("</template>")[0] and "__K__" not in markup
    assert "__TARGET_ORIGIN__" not in h and "__MSG_TYPE__" not in h and SAVE_MESSAGE_TYPE in h
    assert h.count("<script>") == 1
    assert 'id="panel-schedule"' not in h and 'id="panel-budget"' not in h, "new tabs only appear with data"
    assert "Practice drill" not in h or "Try this" in h  # default labels still apply for plain guides

    # v6: trip payload exercises every new section
    trip = run({
        "topic": "Japan 10 days", "archetype": "plan_trip", "lang": 'en"><script>',
        "notice": "Entry rules change; confirm on the official site.",
        "assumptions": ["2 adults", "mid-range budget"],
        "labels": {"drill": "Info", "evil": "x"},
        "schedule": [{"title": "Day 1", "summary": "Arrive",
                      "items": [{"time": "09:00", "title": "Land in Tokyo", "verify": True, "note": "n"}, "Dinner"]},
                     {"title": "empty day", "items": []}],
        "checklist": [{"title": "Packing", "items": ["Passport", "Adapter"]}],
        "budget": {"currency": "JPY", "items": [{"label": "Flights", "estimate": "120,000"},
                                                {"label": "Food"}, {"estimate": 5}]},
        "deadlines": [{"title": "Book flights", "date": "2026-11-01"}, {"title": "Visa", "date": "2026-13-45"}],
        "action_steps": [{"title": "Check passport validity", "details": "Expiry must be 6+ months away."}],
    })
    t = trip["html_app"]
    for needle in ('id="panel-schedule"', 'id="panel-checklist"', 'id="panel-budget"', 'id="panel-deadlines"',
                   'data-f="b0-actual"', 'data-f="d0-0-done"', 'data-f="d0-1-note"', 'data-f="k0-1-done"',
                   'data-f="x0-done"', 'class="notice"', 'class="verify"', '<html lang="en"',
                   'data-est="120000.0"', 'Before you go', 'data-step="Task"', "Info"):
        assert needle in t, f"trip missing {needle}"
    assert "<script>alert" not in t and 'en"><script' not in t
    assert t.count("<script>") == 1
    assert "evil" not in t
    assert len(trip["warnings"]) >= 3, trip["warnings"]   # empty day, label-less budget row, bad date
    _check_keys(t)

    # sparse and wrong-typed new inputs must never break the build
    odd = run({"topic": "x", "archetype": "wat", "schedule": "nope", "checklist": [1, 2],
               "budget": {"items": "x"}, "deadlines": [None], "labels": "bad", "assumptions": 5})
    assert odd["html_app"] and "failed" not in odd["summary"]
    assert any("unknown archetype" in w for w in odd["warnings"])
    print("self-test ok;", len(out["warnings"]) + len(trip["warnings"]), "warnings;", len(t), "bytes")


try:
    _INPUTS = inputs  # injected by SkillExecutor
except NameError:
    _INPUTS = None

if _INPUTS is not None:
    result = run(_INPUTS)
elif __name__ == "__main__":
    _selftest()
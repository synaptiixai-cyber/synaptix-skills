"""Mentor Guide HTML app builder (v6.1, sandbox-lean).

Runtime contract: SkillExecutor injects a global `inputs`; this script sets a
global `result` = {"html_app", "summary", "warnings"}. Stdlib only: json, re,
html, hashlib. html_app is wrapped in synaptix-html-app markers.

Client state: the DOM is the source of truth. Every editable control has a
stable data-f key: s0-done|due|note (steps), c1-title|done|due|note (user
milestones), l0-note, v0-note, d0-1-done|note (schedule), k0-1-done
(checklist), b0-actual (budget), x0-done (deadlines), target, target-text,
journal. Normalizers return HTML-escaped text, so renderers only interpolate.
"""
import hashlib
import html as _html
import json
import re

MAX_ITEMS = 60
MAX_TEXT = 6000
MAX_TITLE = 300
MAX_QUOTE_WORDS = 30
# Set to the host's exact origin in production: the save bar posts user notes.
SAVE_TARGET_ORIGIN = "*"
SAVE_MESSAGE_TYPE = "synaptix-html-app-save"
WEB_FONTS = True
HUES = (4, 22, 150, 175, 200, 222, 340)
DEPTHS = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}
LABELS = {
    "overview": "Overview", "lessons": "Key lessons", "action": "Action plan",
    "schedule": "Schedule", "checklist": "Checklists", "budget": "Budget",
    "deadlines": "Deadlines", "step": "Step", "drill": "Practice drill", "tips": "Try this",
}
ARCH = {
    "learn_skill": {},
    "understand_subject": {"drill": "Activity", "tips": "Key points"},
    "exam_prep": {"action": "Study plan", "drill": "Study task", "tips": "Key points"},
    "plan_trip": {"action": "Before you go", "drill": "Details", "tips": "Good to know", "step": "Task"},
    "plan_event": {"action": "Preparation", "drill": "Details", "tips": "Good to know", "step": "Task"},
    "build_project": {"action": "Milestones", "drill": "Deliverable", "tips": "Watch out for", "step": "Milestone"},
    "decision": {"action": "How to decide", "drill": "Do this", "tips": "Consider"},
    "habit": {"action": "Experiments", "drill": "Experiment", "tips": "Try this", "step": "Experiment"},
    "other": {},
}

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_URL = re.compile(r"^https?://([^/?#:]+)(?::\d+)?(/[^?#]*)?(?:\?([^#]*))?", re.IGNORECASE)
_YT_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
             "youtu.be", "www.youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com")
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_TS = re.compile(r"^(?:\d{1,2}:)?\d{1,2}:\d{2}$")
_TS_LINE = re.compile(r"^\s*\[?((?:\d{1,2}:)?\d{1,2}:\d{2})\]?\s*[-\u2013\u2014:]?\s*(.*)$")
_LANG = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")
_DATE = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")
_PLACEHOLDER = re.compile(r"^(?:add a note|your note.*|note|placeholder|tbd|n/a|\d+(?:\.\d+)?)$", re.IGNORECASE)

_L = {}   # active labels (already escaped), refreshed once per build
W = []    # warnings


def warn(msg):
    if len(W) < 25:
        W.append(msg)


# -- helpers ------------------------------------------------------------------

def esc(v):
    return _html.escape("" if v is None else str(v), quote=True)


def txt(v, n=MAX_TEXT):
    if v is None or isinstance(v, (dict, list, tuple, set)):
        return ""
    return _CTRL.sub("", str(v)).strip()[:n].rstrip()


def tx(v, n=MAX_TEXT):
    return esc(txt(v, n))


def clip(s, n):
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(",;:.- ") + "\u2026"


def as_list(v):
    if isinstance(v, str):
        s = v.strip()
        try:
            v = json.loads(s) if s[:1] in ("[", "{") else ([s] if s else [])
        except ValueError:
            v = [s]
    if isinstance(v, dict):
        return [v]
    return list(v)[:MAX_ITEMS] if isinstance(v, (list, tuple)) else []


def strs(v, n=500):
    if isinstance(v, str):
        v = re.split(r"\n+", v)
    out = []
    for item in (v if isinstance(v, (list, tuple)) else [])[:MAX_ITEMS]:
        t = re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s*", "", txt(item, n))
        if t:
            out.append(esc(t))
    return out


def first(d, *keys):
    for k in keys:
        if d.get(k) not in (None, "", [], {}):
            return d[k]
    return ""


def safe_url(u):
    u = _CTRL.sub("", str(u or "")).strip()
    return u if u and len(u) <= 2048 and _URL.match(u) else ""


def youtube_id(u):
    m = _URL.match(u)
    if not m or m.group(1).lower() not in _YT_HOSTS:
        return ""
    host, path, q = m.group(1).lower(), m.group(2) or "/", m.group(3) or ""
    if host.endswith("youtu.be"):
        c = path.lstrip("/")[:11]
    else:
        mv = re.search(r"(?:^|&)v=([^&#]+)", q) or re.match(r"^/(?:embed|shorts|live|v)/([^/?#]+)", path)
        c = mv.group(1) if mv else ""
    return c if _YT_ID.match(c) else ""


def secs(ts):
    ts = txt(ts, 12)
    if not _TS.match(ts):
        return None
    n = 0
    for p in ts.split(":"):
        n = n * 60 + int(p)
    return n


def hue(topic):
    return HUES[int(hashlib.sha256(topic.encode("utf-8")).hexdigest(), 16) % len(HUES)]


def num(v):
    try:
        n = float(re.sub(r"[^0-9.]", "", "" if v is None or isinstance(v, (dict, list, bool)) else str(v)))
    except ValueError:
        return None
    return n if n < 1e12 else None


# -- normalizers (all text returned escaped) ------------------------------------

def blueprint(inp):
    a = txt(inp.get("archetype"), 40).lower()
    if a and a not in ARCH:
        warn("unknown archetype '%s'; using 'other'" % a)
        a = "other"
    lab = dict(LABELS)
    lab.update(ARCH.get(a, {}))
    raw = inp.get("labels")
    if isinstance(raw, dict):
        for k in raw:
            if k in LABELS and txt(raw[k], 30):
                lab[k] = txt(raw[k], 30)
    _L.clear()
    for k in lab:
        _L[k] = esc(lab[k])
    lang = txt(inp.get("lang"), 12)
    return tx(inp.get("notice"), 600), strs(inp.get("assumptions"), 160)[:8], lang if _LANG.match(lang) else "en"


def lessons(raw):
    out = []
    for i, it in enumerate(as_list(raw)):
        d = it if isinstance(it, dict) else {"description": it}
        desc = txt(first(d, "description", "desc", "text"))
        title = txt(first(d, "title", "name"), MAX_TITLE) or clip(desc, 60)
        if not title:
            warn("key_lessons[%d] had no usable text and was skipped" % i)
            continue
        out.append((esc(title), esc(desc), strs(first(d, "tips", "key_points")),
                    tx(first(d, "source", "channel", "author"), 120), esc(clip(desc, 170))))
    return out


def quotes(raw):
    out = []
    for i, it in enumerate(as_list(raw)):
        d = it if isinstance(it, dict) else {"text": it}
        t = txt(first(d, "text", "quote"), 600)
        if not t or len(t.split()) > MAX_QUOTE_WORDS:
            warn("expert_quotes[%d] was empty or longer than %d words and was skipped" % (i, MAX_QUOTE_WORDS))
        else:
            out.append((esc(t), tx(d.get("author"), 120)))
    return out


def steps(raw):
    out = []
    for i, it in enumerate(as_list(raw)):
        d = it if isinstance(it, dict) else {"title": it}
        t = txt(first(d, "title", "name", "task", "action"), MAX_TITLE)
        if _PLACEHOLDER.match(t.strip()):
            t = ""
        desc = txt(first(d, "description", "desc", "what"))
        if _PLACEHOLDER.match(desc.strip()):
            desc = ""
        if not (t or desc):
            warn("action_steps[%d] had no usable text and was skipped" % i)
            continue
        out.append((esc(t) if t else esc(clip(desc, 60)), esc(desc),
                    tx(d.get("duration"), 40), tx(first(d, "details", "drill"))))
    return out


def stamps(raw):
    out = []
    for it in as_list(raw):
        if isinstance(it, dict):
            t, lab = txt(first(it, "time", "timestamp"), 12), txt(it.get("label"), 200)
        else:
            m = _TS_LINE.match(txt(it, 240))
            t, lab = (m.group(1), m.group(2)) if m else ("", "")
        s = secs(t)
        if s is not None:
            out.append((esc(t), s, esc(lab)))
    return out


def videos(raw):
    out, seen = [], set()
    for i, it in enumerate(as_list(raw)):
        u = safe_url(it.get("url")) if isinstance(it, dict) else ""
        if not u:
            warn("videos[%d] has no valid http(s) url and was skipped" % i)
        elif u not in seen:
            seen.add(u)
            out.append((esc(u), youtube_id(u), tx(it.get("title"), MAX_TITLE) or "Untitled video",
                        tx(first(it, "channel", "author"), 120), tx(it.get("duration"), 30),
                        tx(first(it, "transcript_summary", "summary"), 1200),
                        strs(first(it, "takeaways", "notes")), stamps(it.get("key_timestamps"))))
    return out


def web(raw):
    flat = []
    for it in as_list(raw):
        if isinstance(it, dict) and isinstance(it.get("results"), list):
            flat += [r for r in it["results"][:MAX_ITEMS] if isinstance(r, dict)]
        else:
            flat.append(it)
    out, seen = [], set()
    for i, it in enumerate(flat):
        u = safe_url(it.get("url")) if isinstance(it, dict) else ""
        if not u:
            warn("web_sources[%d] has no valid http(s) url and was skipped" % i)
        elif u not in seen:
            seen.add(u)
            host = _URL.match(u).group(1).lower().removeprefix("www.")
            out.append((esc(u), tx(it.get("title"), MAX_TITLE) or esc(host), esc(host)))
    return out[:MAX_ITEMS]


def schedule(raw):
    out = []
    for gi, g in enumerate(as_list(raw)):
        items = []
        for it in (as_list(first(g, "items", "activities", "tasks", "events", "plan")) if isinstance(g, dict) else []):
            d = it if isinstance(it, dict) else {"title": it}
            t = txt(first(d, "title", "name", "activity", "task", "event"), MAX_TITLE)
            if not t or _PLACEHOLDER.match(t.strip()):
                continue
            nt = txt(first(d, "note", "details", "description"), 800)
            if _PLACEHOLDER.match(nt.strip()):
                nt = ""
            tm = txt(first(d, "time", "when"), 40)
            if _PLACEHOLDER.match(tm.strip()):
                tm = ""
            items.append((esc(t), tx(nt, 800), tx(tm, 40), bool(d.get("verify"))))
        if items:
            g_title = tx(first(g, "title", "day", "phase", "week"), MAX_TITLE)
            if not g_title or _PLACEHOLDER.match(g_title.strip()):
                g_title = "Day %d" % (len(out) + 1)
            out.append((g_title, tx(g.get("summary"), 300), items))
        else:
            warn("schedule[%d] had no items and was skipped" % gi)
    return out


def checklist(raw):
    out = []
    for gi, g in enumerate(as_list(raw)):
        items = strs(g.get("items"), 200) if isinstance(g, dict) else []
        if items:
            out.append((tx(g.get("title"), MAX_TITLE) or "Checklist", items))
        else:
            warn("checklist[%d] had no items and was skipped" % gi)
    return out


def budget(raw):
    items = []
    if isinstance(raw, dict):
        for i, it in enumerate(as_list(raw.get("items"))):
            lab = txt(first(it, "label", "title", "name"), 160) if isinstance(it, dict) else ""
            if lab:
                items.append((esc(lab), num(first(it, "estimate", "amount")), bool(it.get("verify"))))
            else:
                warn("budget.items[%d] had no label and was skipped" % i)
    return (tx(raw.get("currency"), 8), items) if items else None


_GENERIC = re.compile(r"^(?:task|step|day|activity|item|practice|session|study|review|milestone|to do|add a note|note)\s*\d*$|^\d+(?:\.\d+)?$", re.I)


def lint(sch, st):
    """Warn (never fail) when step or schedule titles are generic or copied."""
    titles = [s[0] for s in st] + [i[0] for g in sch for i in g[2]]
    seen, bad = set(), 0
    for t in titles:
        k = " ".join(t.lower().split())
        if _GENERIC.match(k) or (len(k.split()) >= 3 and k in seen):
            bad += 1
        seen.add(k)
    if bad >= 2 or (bad and bad * 4 >= len(titles)):
        warn("GENERIC: %d of %d step/schedule titles are generic or duplicated. "
             "Rewrite each as a specific verb plus object and rebuild once." % (bad, len(titles)))


def deadlines(raw):
    out = []
    for i, it in enumerate(as_list(raw)):
        t = txt(first(it, "title", "name"), MAX_TITLE) if isinstance(it, dict) else ""
        if not t:
            warn("deadlines[%d] had no title and was skipped" % i)
            continue
        d = txt(it.get("date"), 10)
        if d and not _DATE.match(d):
            warn("deadlines[%d] date is not a valid YYYY-MM-DD and was ignored" % i)
            d = ""
        out.append((d or "9999", d, esc(t), tx(it.get("note"), 400)))
    out.sort()
    return out


# -- static markup --------------------------------------------------------------

PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M8 5v14l11-7z"/></svg>'
BADGE = '<span class="badge" id="note-count" hidden>0</span>'
TARGET = ('<div class="target"><label class="field" for="target-text"><span>Your finish line</span>'
          '<input type="text" class="text-in" id="target-text" data-f="target-text" maxlength="120" '
          'placeholder="What does success look like?"></label>'
          '<label class="field" for="target"><span>Target completion date</span>'
          '<input type="date" class="date" id="target" data-f="target"></label></div>')
NOTES = ('<h2>Notes and journal</h2><p class="j-summary" id="j-summary"></p>'
         '<section aria-labelledby="j1"><h3 class="j-h" id="j1">Timeline</h3><div id="j-timeline"></div></section>'
         '<section aria-labelledby="j2"><h3 class="j-h" id="j2">Your notes</h3><div id="j-takeaways"></div></section>'
         '<section aria-labelledby="j3"><h3 class="j-h" id="j3">Journal</h3>'
         '<label class="sr-only" for="journal">Freeform journal</label>'
         '<textarea class="journal" id="journal" data-f="journal" maxlength="16000" rows="10" '
         'placeholder="What worked, what to change next."></textarea></section>')
BUDGET_HEAD = ('</h2><div class="tablewrap"><table class="budget" id="budget" data-cur="')
BUDGET_TOP = ('"><thead><tr><th scope="col">Item</th><th scope="col">Estimate</th><th scope="col">Actual</th></tr></thead><tbody>')
BUDGET_FOOT = ('</tbody><tfoot><tr><th scope="row">Total</th><td id="b-est"></td><td id="b-act"></td></tr>'
               '<tr><th scope="row">Difference (entered items)</th><td></td><td id="b-diff"></td></tr></tfoot></table></div>'
               '<p class="g-sum">Estimates are planning figures. Confirm real prices before paying.</p>')
SAVEBAR = ('<div class="savebar" id="savebar" role="region" aria-label="Save your changes" hidden>'
           '<span id="bar-msg"></span><button type="button" class="savebtn" id="save">Save augmented guide</button></div>'
           '<p class="sr-only" id="save-live" aria-live="polite"></p>')


# -- renderers (inputs are already escaped) -------------------------------------

def panel(n, body):
    h = "" if n == "overview" else " hidden"
    return f'<section class="panel" id="panel-{n}" role="tabpanel" aria-labelledby="tab-{n}" tabindex="0"{h}>{body}</section>'


def note(f, empty, aria, ph=""):
    return (f'<details class="note"><summary data-empty="{empty}" data-filled="Your note">{empty}</summary>'
            f'<textarea class="note-input" data-f="{f}" maxlength="4000" rows="3" aria-label="{aria}" placeholder="{ph}"></textarea></details>')


def paras(t):
    return "".join("<p>%s</p>" % p.strip() for p in re.split(r"\n\s*\n", t) if p.strip())


def quote(q, cls="quote"):
    t, a = q
    cap = f"<figcaption>{a}</figcaption>" if a else ""
    return f'<figure class="{cls}"><blockquote><p>{t}</p></blockquote>{cap}</figure>'


def overview(topic, goal, level, notice, assume, jumps, les, qs):
    lv = f'<p class="level">{level} guide</p>' if level else ""
    hq = quote(qs[0], "quote hero-quote") if qs else ""
    jb = "".join(f'<li><button type="button" class="jump" data-goto="{n}">{lab} <strong>{c}</strong></button></li>'
                 for n, lab, c in jumps if c)
    jh = f'<ul class="jumps">{jb}</ul>' if jb else ""
    nt = f'<aside class="notice" role="note"><strong>Before you start.</strong> {notice}</aside>' if notice else ""
    asm = ""
    if assume:
        asm = ('<section class="assume" aria-labelledby="as-h"><h2 id="as-h">Assumptions</h2><ul>'
               + "".join("<li>%s</li>" % a for a in assume) + "</ul></section>")
    pv = ""
    if les:
        pv = ('<section class="preview" aria-labelledby="pv-h"><h2 id="pv-h">Worth knowing first</h2><ul>'
              + "".join(f"<li><strong>{t}</strong> {sn}</li>" for t, _, _, _, sn in les[:3]) + "</ul></section>")
    return (f'<header class="hero"><div class="hero-meta">{lv}<p class="ver" id="ver">Version 1, AI original</p></div>'
            f'<h1>{topic}</h1><p class="goal">{goal}</p>{TARGET}{hq}</header>{nt}{asm}{jh}{pv}')


def lessons_panel(les, qs):
    items = []
    for i, (t, d, tips, src, _) in enumerate(les):
        s = f'<p class="source">From {src}</p>' if src else ""
        tp = ""
        if tips:
            tp = (f'<div class="tips"><p class="tips-h">{_L["tips"]}</p><ul>'
                  + "".join("<li>%s</li>" % x for x in tips) + "</ul></div>")
        nb = note("l%d-note" % i, "Add your own note", "Your note on this lesson", "How will you apply this?")
        items.append(f'<article class="lesson"><h3>{t}</h3>{s}<div class="prose">{paras(d)}</div>{tp}{nb}</article>')
    qb = ""
    if qs:
        qb = ('<section class="quotes" aria-labelledby="q-h"><h2 id="q-h">In their words</h2>'
              + "".join(quote(q) for q in qs) + "</section>")
    return f'<h2 class="sr-only">{_L["lessons"]}</h2>' + "".join(items) + qb


def step(key, n, s, custom=False):
    t, d, dur, drill = s
    du = f"<span>{dur}</span>" if dur else ""
    ds = f'<div class="prose">{paras(d)}</div>' if d else ""
    dr = f'<div class="drill"><p class="drill-h">{_L["drill"]}</p><p>{drill}</p></div>' if drill else ""
    if custom:
        ck = ' aria-label="Mark this milestone done"'
        ti = (f'<input type="text" class="custom-title" data-f="{key}-title" maxlength="120" '
              'aria-label="Milestone name" placeholder="Name your milestone">')
        yours = " (yours)"
        rm = '<button type="button" class="ghost rm" data-remove>Remove</button>'
        cls = "step custom"
    else:
        ck, yours, rm, cls = "", "", "", "step"
        ti = f'<label class="step-title" for="chk-{key}">{t}</label>'
    nb = note(f"{key}-note", "Add a note", "Your notes for this item", "What went well, what got in the way?")
    return (f'<li class="{cls}" data-key="{key}"><input type="checkbox" class="chk" id="chk-{key}" data-f="{key}-done"{ck} aria-describedby="sm-{key}">'
            f'<div class="step-body"><p class="step-meta" id="sm-{key}"><span>{_L["step"]} <span class="num">{n}</span>{yours}</span>{du}</p>'
            f'{ti}{ds}{dr}<div class="step-plan"><label class="due-field" for="due-{key}"><span>Target date</span>'
            f'<input type="date" class="date" id="due-{key}" data-f="{key}-due"></label>{rm}</div>{nb}</div></li>')


def action_panel(st):
    rows = "".join(step("s%d" % i, i + 1, s) for i, s in enumerate(st))
    blank = step("__K__", 0, ("", "", "", ""), True)
    return (f'<div class="action-head"><h2>{_L["action"]}</h2>'
            '<button type="button" class="ghost" id="reset">Uncheck all steps</button></div>'
            f'<ol class="steps" id="steps">{rows}</ol>'
            '<button type="button" class="add-step" id="add-step">Add your own milestone</button>'
            f'<template id="tpl-step">{blank}</template>')


def schedule_panel(sch):
    out = []
    for gi, (title, summ, items) in enumerate(sch):
        rows = []
        for ii, (t, nt, tm, ver) in enumerate(items):
            k = f"d{gi}-{ii}"
            tms = f'<span class="s-time">{tm}</span>' if tm else ""
            vf = '<span class="verify">Verify</span>' if ver else ""
            nn = f'<p class="s-note">{nt}</p>' if nt else ""
            nb = note(k + "-note", "Add a note", "Your note on " + t)
            rows.append(f'<li class="sitem"><input type="checkbox" class="sdone" id="chk-{k}" data-f="{k}-done">'
                        f'<div class="sbody"><p class="s-head">{tms}<label for="chk-{k}" class="s-title">{t}</label>{vf}</p>{nn}{nb}</div></li>')
        sm = f'<p class="g-sum">{summ}</p>' if summ else ""
        out.append(f'<section class="group"><h2>{title}</h2>{sm}<ul class="slist">{"".join(rows)}</ul></section>')
    return f'<h2 class="sr-only">{_L["schedule"]}</h2>' + "".join(out)


def checklist_panel(ck):
    out = []
    for gi, (t, items) in enumerate(ck):
        rows = "".join(f'<li class="citem"><input type="checkbox" class="cdone" id="chk-k{gi}-{ii}" data-f="k{gi}-{ii}-done">'
                       f'<label for="chk-k{gi}-{ii}">{x}</label></li>' for ii, x in enumerate(items))
        out.append(f'<section class="group"><h2>{t}</h2><ul class="clist">{rows}</ul></section>')
    return f'<h2 class="sr-only">{_L["checklist"]}</h2>' + "".join(out)


def budget_panel(b):
    cur, items = b
    rows = []
    for i, (lab, est, ver) in enumerate(items):
        vf = ' <span class="verify">Verify</span>' if ver else ""
        da = f' data-est="{est}"' if est is not None else ""
        es = f"{est:,.2f}" if est is not None else "n/a"
        rows.append(f'<tr><th scope="row">{lab}{vf}</th><td{da}>{es}</td><td><input type="number" min="0" step="any" '
                    f'inputmode="decimal" class="num-in" data-f="b{i}-actual" aria-label="Actual cost: {lab}"></td></tr>')
    return f'<h2>{_L["budget"]}' + BUDGET_HEAD + cur + BUDGET_TOP + "".join(rows) + BUDGET_FOOT


def deadlines_panel(dl):
    rows = []
    for i, (_, d, t, n) in enumerate(dl):
        nn = f'<p class="s-note">{n}</p>' if n else ""
        rows.append(f'<li class="sitem"><input type="checkbox" class="sdone" id="chk-x{i}" data-f="x{i}-done"><div class="sbody">'
                    f'<p class="s-head"><span class="j-date" data-date="{d}">{d or "No date"}</span>'
                    f'<label for="chk-x{i}" class="s-title">{t}</label></p>{nn}</div></li>')
    return f'<h2>{_L["deadlines"]}</h2><ul class="slist">{"".join(rows)}</ul>'


def videos_html(vs):
    cards = []
    for i, (u, vid, title, ch, dur, summ, tk, sts) in enumerate(vs):
        pl = ""
        if vid:
            pl = (f'<div class="player" data-vid="{vid}" data-title="{title}"><button type="button" class="facade" aria-label="Play video: {title}">'
                  f'<img class="facade-img" src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="" loading="lazy">'
                  f'<span class="play">{PLAY}</span></button></div>')
        meta = "".join("<span>%s</span>" % x for x in (ch, dur) if x)
        sm = f'<p class="vsummary">{summ}</p>' if summ else ""
        tp = ""
        if tk:
            tp = ('<div class="tips"><p class="tips-h">Takeaways</p><ul>'
                  + "".join("<li>%s</li>" % x for x in tk) + "</ul></div>")
        ts = ""
        if sts:
            sep = "&amp;" if "?" in u else "?"
            ls = "".join(f'<li><a class="ts" href="{u}{sep}t={s}s" target="_blank" rel="noopener noreferrer" data-seek="{s}">'
                         f'<span class="ts-time">{t}</span><span>{lab}</span></a></li>' for t, s, lab in sts)
            ts = f'<ul class="stamps" aria-label="Jump to a moment">{ls}</ul>'
        nb = note(f"v{i}-note", "Add notes or bookmarks", "Your notes on this video", "e.g. 5:30, rewatch before practice")
        cards.append(f'<article class="video">{pl}<div class="video-body"><h3><a href="{u}" target="_blank" rel="noopener noreferrer">{title}</a></h3>'
                     f'<p class="meta">{meta}</p>{sm}{tp}{ts}{nb}</div></article>')
    if not cards:
        return ""
    return f'<section aria-labelledby="v-h"><h2 id="v-h">Videos</h2><div class="videos">{"".join(cards)}</div></section>'


def resources_panel(vs, ws):
    wl = ""
    if ws:
        ls = "".join(f'<li><a href="{u}" target="_blank" rel="noopener noreferrer"><span class="wl-title">{t}</span>'
                     f'<span class="wl-host">{h}</span></a></li>' for u, t, h in ws)
        wl = f'<section aria-labelledby="w-h"><h2 id="w-h">Further reading</h2><ul class="weblinks">{ls}</ul></section>'
    return videos_html(vs) + wl


# -- CSS / JS (plain strings) ---------------------------------------------------

CSS = r"""
:root{
  color-scheme: light dark;
  --bg:hsl(var(--h),28%,97%); --surface:hsl(var(--h),30%,99%);
  --ink:hsl(var(--h),35%,11%); --muted:hsl(var(--h),14%,36%);
  --rule:hsl(var(--h),18%,84%); --accent:hsl(var(--h),72%,30%);
  --accent-bg:hsl(var(--h),55%,92%); --focus:hsl(var(--h),85%,40%);
  --field-bd:hsl(var(--h),12%,50%);
  --serif:'Fraunces',Georgia,'Times New Roman',serif;
  --sans:'Instrument Sans',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  --measure:68ch;
}
@media (prefers-color-scheme:dark){:root{
  --bg:hsl(var(--h),22%,9%); --surface:hsl(var(--h),20%,12%);
  --ink:hsl(var(--h),25%,93%); --muted:hsl(var(--h),12%,70%);
  --rule:hsl(var(--h),14%,23%); --accent:hsl(var(--h),78%,72%);
  --accent-bg:hsl(var(--h),32%,18%); --focus:hsl(var(--h),90%,70%);
  --field-bd:hsl(var(--h),10%,52%);
}}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:400 16px/1.65 var(--sans);-webkit-font-smoothing:antialiased}
h1,h2,h3,p,ul,ol,figure,blockquote{margin:0}
ul,ol{padding:0;list-style:none}
a{color:inherit}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px;border-radius:4px}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}

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

main{max-width:860px;margin:0 auto;padding:40px 20px 96px}
.panel[hidden]{display:none}
.panel:focus:not(:focus-visible){outline:none}
h2{font:700 1.375rem/1.3 var(--serif);margin-bottom:16px}
h3{font:700 1.125rem/1.35 var(--serif)}
.prose{max-width:var(--measure)}
.prose p+p{margin-top:.8em}

.hero{padding:24px 0 40px;border-bottom:1px solid var(--rule);margin-bottom:32px}
.hero-meta{display:flex;flex-wrap:wrap;align-items:center;gap:6px 16px;margin-bottom:20px}
.level{display:inline-block;font-size:14px;font-weight:600;color:var(--accent);border-left:3px solid var(--accent);padding-left:10px}
.ver{font-size:13px;color:var(--muted)}
h1{font:700 clamp(2.1rem,6vw,3.6rem)/1.1 var(--serif);letter-spacing:-.015em;max-width:18ch}
.goal{font-family:var(--serif);font-size:1.2rem;line-height:1.6;color:var(--muted);max-width:52ch;margin-top:20px}
.hero-quote{margin-top:32px}
.quote{border-left:3px solid var(--rule);padding:2px 0 2px 20px;max-width:56ch}
.quote blockquote p{font:italic 400 1.125rem/1.6 var(--serif)}
.quote figcaption{margin-top:8px;font-size:14px;color:var(--muted)}
.quote+.quote{margin-top:24px}
.target{display:flex;flex-wrap:wrap;gap:14px 20px;margin-top:28px;max-width:600px}
.field{display:flex;flex-direction:column;gap:4px;font-size:14px;color:var(--muted);flex:1 1 220px}
.field:last-child{flex:0 1 200px}

.jumps{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:40px}
.jump{font:500 15px/1 var(--sans);color:var(--ink);background:var(--surface);border:1px solid var(--rule);
  border-radius:8px;padding:14px 16px;cursor:pointer;min-height:44px}
.jump:hover{border-color:var(--accent)}
.jump strong{color:var(--accent);font-weight:700;margin-left:4px}
.preview li{padding:14px 0;border-top:1px solid var(--rule);max-width:var(--measure)}
.preview li:first-child{border-top:0}
.notice{margin:0 0 32px;padding:14px 18px;border:1px solid var(--accent);border-left-width:4px;
  background:var(--accent-bg);border-radius:8px;max-width:var(--measure);font-size:15px}
.assume{margin-bottom:40px}
.assume li{position:relative;padding:4px 0 4px 16px;font-size:15px}
.assume li::before{content:"";position:absolute;left:0;top:.95em;width:6px;height:2px;background:var(--accent)}

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

.action-head{display:flex;align-items:baseline;justify-content:space-between;gap:16px;margin-bottom:8px}
.ghost{font:500 14px/1 var(--sans);color:var(--muted);background:none;border:0;padding:8px;cursor:pointer;
  text-decoration:underline;text-underline-offset:3px;min-height:44px;display:inline-flex;align-items:center}
.ghost:hover{color:var(--ink)}
.step{display:flex;gap:16px;padding:22px 0;border-top:1px solid var(--rule)}
.step:first-child{border-top:0}
.chk{width:22px;height:22px;flex:none;margin-top:2px;accent-color:var(--accent);cursor:pointer}
.step-body{min-width:0}
.step-meta{display:flex;gap:12px;font-size:14px;color:var(--muted);margin-bottom:2px}
.step-meta span:first-child{font-weight:600;color:var(--accent)}
.step-title{display:block;font:700 1.125rem/1.4 var(--serif);cursor:pointer;margin-bottom:6px}
.step.done .step-title{text-decoration:line-through;text-decoration-thickness:1px;color:var(--muted)}
.drill{margin-top:12px;padding:12px 16px;border-left:3px solid var(--accent);background:var(--accent-bg);border-radius:0 8px 8px 0;max-width:var(--measure);font-size:15px}
.step-plan{display:flex;flex-wrap:wrap;align-items:center;gap:8px 20px;margin-top:14px}
.due-field{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--muted)}
.rm{margin-left:auto}
.rm.armed{color:var(--accent);font-weight:600}
.custom-title{display:block;width:100%;font:700 1.125rem/1.4 var(--serif);margin-bottom:6px}
.add-step{font:600 15px/1 var(--sans);color:var(--accent);background:none;border:1px dashed var(--accent);
  border-radius:8px;padding:14px 18px;margin-top:12px;cursor:pointer;min-height:44px}
.add-step:hover{background:var(--accent-bg)}

.date,.text-in,.custom-title,.note-input,.journal,.num-in{font:inherit;color:var(--ink);background:var(--surface);
  border:1px solid var(--field-bd);border-radius:8px;padding:8px 10px;max-width:100%}
.date,.text-in{font-size:15px}
.text-in{width:100%}
.note{margin-top:14px;max-width:var(--measure)}
.note summary{cursor:pointer;font-size:14px;font-weight:600;color:var(--accent);padding:4px 0;width:fit-content;
  min-height:44px;display:flex;align-items:center}
.note-input{display:block;width:100%;margin-top:8px;min-height:84px;resize:vertical;font-size:15px;line-height:1.55}

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
.tablewrap{overflow-x:auto}
.budget{border-collapse:collapse;width:100%;max-width:var(--measure);font-size:15px}
.budget th,.budget td{text-align:left;padding:10px 8px;border-top:1px solid var(--rule)}
.budget thead th{font-size:14px;color:var(--muted);border-top:0}
.budget tfoot{font-weight:700}
.num-in{width:8em}

.panel>section+section{margin-top:48px}
.videos{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:28px 24px}
.player{aspect-ratio:16/9;background:var(--rule);border-radius:10px;overflow:hidden}
.player iframe,.facade{width:100%;height:100%;border:0;display:block}
.facade{position:relative;padding:0;background:var(--rule);cursor:pointer}
.facade[hidden]{display:none}
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

.badge{display:inline-block;min-width:1.5em;margin-left:6px;padding:2px 6px;border-radius:99px;
  background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:700;line-height:1.3;text-align:center}
.badge[hidden]{display:none}
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

.savebar{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:20;display:flex;align-items:center;
  gap:16px;max-width:calc(100% - 24px);padding:10px 12px 10px 18px;background:var(--ink);color:var(--bg);
  border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.28);font-size:14px;animation:barIn .22s ease both}
.savebar[hidden]{display:none}
.savebar :focus-visible{outline-color:var(--bg)}
.savebtn{font:600 14px/1 var(--sans);color:var(--ink);background:var(--bg);border:0;border-radius:8px;padding:12px 14px;cursor:pointer;min-height:44px}
.savebtn:disabled{opacity:.6;cursor:default}
@keyframes barIn{from{opacity:0;transform:translate(-50%,8px)}to{opacity:1;transform:translate(-50%,0)}}

@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.hero>*{animation:rise .55s cubic-bezier(.2,.7,.2,1) both}
.hero>:nth-child(2){animation-delay:.08s}.hero>:nth-child(3){animation-delay:.16s}.hero>:nth-child(4){animation-delay:.28s}
@media (prefers-reduced-motion:reduce){.hero>*{animation:none}.bar{transition:none}.savebar{animation:none}}

@media (max-width:600px){
  main{padding-top:28px}
  .nav-in{padding:0 8px 0 12px;gap:8px}
  .track{display:none}
  .videos{grid-template-columns:1fr}
  .savebar{left:12px;right:12px;transform:none;flex-wrap:wrap;justify-content:space-between;animation:none}
  .step-plan{align-items:flex-start}
}
@media print{
  .nav,.savebar{display:none}
  .panel[hidden]{display:block}
  .panel{break-before:page}
  .panel:first-of-type{break-before:auto}
  main{padding:0}
  .hero>*{animation:none}
}
"""

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
CSP_NOFONT = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
              "img-src https://i.ytimg.com data:; frame-src https://www.youtube-nocookie.com; base-uri 'none'; form-action 'none'")
FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,700;1,9..144,400'
    '&family=Instrument+Sans:wght@400;500;600;700&display=swap">'
)


# -- assembly -------------------------------------------------------------------

def wrap(doc):
    return "<!-- synaptix-html-app -->" + doc + "<!-- /synaptix-html-app -->"


def error_page(msg):
    return wrap('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Guide unavailable</title>'
                '<style>body{font:16px/1.6 system-ui,sans-serif;max-width:520px;margin:15vh auto;padding:0 20px}</style></head>'
                '<body><h1>The guide could not be built</h1><p>' + esc(msg) + '</p></body></html>')


def build(inp):
    t_raw = txt(inp.get("topic"), MAX_TITLE)
    if not t_raw:
        warn("topic was missing; a placeholder title was used")
        t_raw = "Your topic"
    depth = txt(inp.get("depth"), 30).lower()
    level = DEPTHS.get(depth, "")
    if depth and not level:
        warn("unknown depth '%s'; expected beginner, intermediate or advanced" % depth)

    notice, assume, lang = blueprint(inp)   # must run first: it sets the labels
    les = lessons(inp.get("key_lessons"))
    qs = quotes(inp.get("expert_quotes"))
    st = steps(inp.get("action_steps"))
    vs = videos(inp.get("videos"))
    ws = web(inp.get("web_sources"))
    sch = schedule(inp.get("schedule"))
    ck = checklist(inp.get("checklist"))
    bg = budget(inp.get("budget"))
    dl = deadlines(inp.get("deadlines"))
    lint(sch, st)
    goal_raw = txt(inp.get("goal"), 500)
    if not (les or qs or st or vs or ws or sch or ck or bg or dl):
        warn("no lessons, steps, schedule or resources were provided; the guide starts empty")

    ns = sum(len(g[2]) for g in sch)
    nc = sum(len(g[1]) for g in ck)
    nt = len(st) + ns + nc + len(dl)
    jumps = [("lessons", _L["lessons"], len(les)), ("schedule", _L["schedule"], ns),
             ("action", _L["action"], len(st)), ("checklist", _L["checklist"], nc),
             ("budget", _L["budget"], len(bg[1]) if bg else 0), ("deadlines", _L["deadlines"], len(dl)),
             ("resources", "Resources", len(vs) + len(ws))]
    topic = esc(t_raw)
    parts = [
        ("overview", _L["overview"], True,
         overview(topic, esc(goal_raw or "Turn this topic into a clear, doable plan."), level, notice, assume, jumps, les, qs)),
        ("lessons", _L["lessons"], les or qs, lessons_panel(les, qs)),
        ("schedule", _L["schedule"], sch, schedule_panel(sch)),
        ("action", _L["action"], True, action_panel(st)),
        ("checklist", _L["checklist"], ck, checklist_panel(ck)),
        ("budget", _L["budget"], bg, budget_panel(bg) if bg else ""),
        ("deadlines", _L["deadlines"], dl, deadlines_panel(dl)),
        ("notes", "Notes &amp; journal", True, NOTES),
        ("resources", "Resources", vs or ws, resources_panel(vs, ws)),
    ]
    tabs = [p for p in parts if p[2]]

    tab_html = "".join(
        f'<button type="button" class="tab" role="tab" id="tab-{n}" data-panel="{n}" aria-controls="panel-{n}" '
        f'aria-selected="{"false" if i else "true"}" tabindex="{-1 if i else 0}">{lab}{BADGE if n == "notes" else ""}</button>'
        for i, (n, lab, _, _) in enumerate(tabs))
    pt = "0 of %d done" % nt if nt else "Nothing to track yet"
    progress = ('<div class="progress"><div class="track" id="meter" role="progressbar" aria-label="Plan progress" '
                'aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="bar" id="bar"></div></div>'
                f'<span id="prog-text">{pt}</span></div>')
    main = "".join(panel(n, body) for n, _, _, body in tabs)

    key = hashlib.sha256("\x1f".join([t_raw] + [s[0] for s in st]).encode("utf-8")).hexdigest()[:16]
    script = JS.replace("__TARGET_ORIGIN__", json.dumps(SAVE_TARGET_ORIGIN)).replace("__MSG_TYPE__", json.dumps(SAVE_MESSAGE_TYPE))
    fonts = FONT_LINKS if WEB_FONTS else ""
    csp = CSP if WEB_FONTS else CSP_NOFONT
    desc = esc(clip(goal_raw or "Interactive guide for " + t_raw, 160))

    doc = (f'<!DOCTYPE html><html lang="{lang}" style="--h:{hue(t_raw)}"><head><meta charset="UTF-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<meta http-equiv="Content-Security-Policy" content="{esc(csp)}">'
           f'<meta name="description" content="{desc}"><meta name="color-scheme" content="light dark">'
           f'<title>{topic}: guide</title>{fonts}<style>{CSS}</style></head>'
           f'<body><div id="app" data-key="{key}" data-version="1" data-step="{_L["step"]}">'
           f'<nav class="nav" aria-label="Guide sections"><div class="nav-in"><div class="tabs" role="tablist">{tab_html}</div>{progress}</div></nav>'
           f'<main>{main}</main>{SAVEBAR}</div><script>{script}</script></body></html>')
    return wrap(doc)


def run(raw):
    W.clear()
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(data, dict):
            raise TypeError("inputs must be an object")
        html_app = build(data)
        summary = "Guide app built successfully"
        if W:
            summary += " with %d input warning(s)" % len(W)
        return {"html_app": html_app, "summary": summary, "warnings": list(W)}
    except Exception as exc:  # last-resort guard: always return a renderable page
        return {"html_app": error_page(str(exc)), "summary": "Guide build failed", "warnings": W + [str(exc)]}


result = run(inputs)

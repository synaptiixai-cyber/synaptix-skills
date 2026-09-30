"""
build_app.py - Mentor Guide HTML app builder (v4.0, production)

Runtime contract (unchanged from v3):
  - Executed by SkillExecutor via run_script(); a global `inputs` dict is injected.
  - stdlib only.
  - Sets a global `result` dict: {"html_app": str, "summary": str, "warnings": [str]}
  - html_app is wrapped in <!-- synaptix-html-app --> ... <!-- /synaptix-html-app -->

What changed in v4 (see the review notes in the chat for rationale):
  Reliability   Never raises on malformed input. Every list item is coerced
                (dict, str, or junk). JSON-encoded strings are accepted.
                Problems become `warnings`, not crashes. Hard failure still
                returns a valid error page.
  Security      Strict URL allowlist (http/https only), escaping everywhere,
                no inline event handlers, CSP meta tag, size caps on all text
                and lists, YouTube ids validated by parsed host, not regex.
  Correctness   Step state keyed by index with a content-derived storage key
                (no id mismatch). Video metadata/timestamps survive
                normalization. Unknown depth is reported, not silently
                relabelled.
  Accessibility WAI-ARIA tabs with roving tabindex and arrow keys, labelled
                checkboxes, live progress region, visible focus, reduced
                motion, light and dark schemes, AA contrast tokens.
  Performance   YouTube facade (no iframes until clicked), timestamp seeking
                via iframe `start=` (no postMessage handshake to break),
                non-blocking font load with real fallbacks.
  Design        Follows the frontend-design brief: no emoji icons, no ALL CAPS
                labels, no card-on-everything, numbering only where content is
                a sequence (action steps), one orchestrated load animation.
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
WEB_FONTS = True        # False => system fonts only, zero external requests
HUES = (4, 22, 150, 175, 200, 222, 340)   # avoids stock indigo/purple and lime
DEPTHS = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_YT_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtu.be", "www.youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com",
}
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_TS = re.compile(r"^(?:\d{1,2}:)?\d{1,2}:\d{2}$")
_TS_LINE = re.compile(r"^\s*\[?((?:\d{1,2}:)?\d{1,2}:\d{2})\]?\s*[-\u2013\u2014:]?\s*(.*)$")


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


# -- Normalizers --------------------------------------------------------------

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
        if text:
            out.append({"text": text, "author": author})
        else:
            warn(f"expert_quotes[{i}] had no text and was skipped")
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
        out.append({"title": title or f"Step {len(out) + 1}", "desc": desc, "dur": dur, "drill": drill})
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


# -- Rendering ----------------------------------------------------------------

def paras(text: str) -> str:
    return "".join(f"<p>{esc(p.strip())}</p>" for p in re.split(r"\n\s*\n", text) if p.strip())


def render_quote(q: dict, cls: str = "quote") -> str:
    cite = f"<figcaption>{esc(q['author'])}</figcaption>" if q["author"] else ""
    return f'<figure class="{cls}"><blockquote><p>{esc(q["text"])}</p></blockquote>{cite}</figure>'


def render_overview(ctx) -> str:
    c = ctx
    level = f'<p class="level">{esc(c["level"])} guide</p>' if c["level"] else ""
    goal = c["goal"] or "Learn this topic and put it to work."
    hero_quote = render_quote(c["quotes"][0], "quote hero-quote") if c["quotes"] else ""

    jumps = []
    for name, n, singular, plural in (
        ("lessons", len(c["lessons"]), "key lesson", "key lessons"),
        ("action", len(c["steps"]), "action step", "action steps"),
        ("resources", len(c["videos"]) + len(c["web"]), "resource", "resources"),
    ):
        if n:
            jumps.append(
                f'<li><button type="button" class="jump" data-goto="{name}">'
                f'<strong>{n}</strong> {singular if n == 1 else plural}</button></li>'
            )
    jump_html = f'<ul class="jumps">{"".join(jumps)}</ul>' if jumps else ""

    preview = ""
    if c["lessons"]:
        rows = []
        for l in c["lessons"][:3]:
            head = l["title"] or clip(l["desc"], 70)
            body = clip(l["desc"], 170) if l["title"] else ""
            rows.append(f"<li><strong>{esc(head)}</strong>{(' ' + esc(body)) if body else ''}</li>")
        preview = f'<section class="preview" aria-labelledby="pv-h"><h2 id="pv-h">Worth knowing first</h2><ul>{"".join(rows)}</ul></section>'

    return (
        '<section class="panel" id="panel-overview" role="tabpanel" aria-labelledby="tab-overview" tabindex="0">'
        f'<header class="hero">{level}<h1>{esc(c["topic"])}</h1><p class="goal">{esc(goal)}</p>{hero_quote}</header>'
        f'{jump_html}{preview}</section>'
    )


def render_lessons(ctx) -> str:
    items = []
    for l in ctx["lessons"]:
        title = f'<h3>{esc(l["title"])}</h3>' if l["title"] else ""
        src = f'<p class="source">From {esc(l["source"])}</p>' if l["source"] else ""
        tips = ""
        if l["tips"]:
            lis = "".join(f"<li>{esc(t)}</li>" for t in l["tips"])
            tips = f'<div class="tips"><p class="tips-h">Try this</p><ul>{lis}</ul></div>'
        items.append(f'<article class="lesson">{title}{src}<div class="prose">{paras(l["desc"])}</div>{tips}</article>')
    quotes = ""
    if ctx["quotes"]:
        quotes = ('<section class="quotes" aria-labelledby="q-h"><h2 id="q-h">In their words</h2>'
                  + "".join(render_quote(q) for q in ctx["quotes"]) + "</section>")
    return (
        '<section class="panel" id="panel-lessons" role="tabpanel" aria-labelledby="tab-lessons" tabindex="0" hidden>'
        f'<h2 class="sr-only">Key lessons</h2>{"".join(items)}{quotes}</section>'
    )


def render_action(ctx) -> str:
    rows = []
    for i, s in enumerate(ctx["steps"]):
        n = i + 1
        dur = f'<span>{esc(s["dur"])}</span>' if s["dur"] else ""
        desc = f'<div class="prose">{paras(s["desc"])}</div>' if s["desc"] else ""
        drill = (f'<div class="drill"><p class="drill-h">Practice drill</p><p>{esc(s["drill"])}</p></div>'
                 if s["drill"] else "")
        rows.append(
            f'<li class="step" data-i="{i}">'
            f'<input type="checkbox" class="chk" id="chk-{i}" aria-describedby="sm-{i}">'
            f'<div class="step-body"><p class="step-meta" id="sm-{i}"><span>Step {n}</span>{dur}</p>'
            f'<label class="step-title" for="chk-{i}">{esc(s["title"])}</label>{desc}{drill}</div></li>'
        )
    return (
        '<section class="panel" id="panel-action" role="tabpanel" aria-labelledby="tab-action" tabindex="0" hidden>'
        '<div class="action-head"><h2>Your plan</h2>'
        '<button type="button" class="ghost" id="reset">Clear progress</button></div>'
        f'<ol class="steps">{"".join(rows)}</ol></section>'
    )


_PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M8 5v14l11-7z"/></svg>'


def render_videos(videos) -> str:
    cards = []
    for v in videos:
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
        cards.append(
            f'<article class="video">{player}<div class="video-body">'
            f'<h3><a href="{esc(v["url"])}" target="_blank" rel="noopener noreferrer">{esc(v["title"])}</a></h3>'
            f'<p class="meta">{meta}</p>{summary}{take}{stamps}</div></article>'
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
.panel:focus{outline:none}
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
  border-radius:8px;padding:12px 16px;cursor:pointer}
.jump:hover{border-color:var(--accent)}
.jump strong{color:var(--accent);font-weight:700}
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
section+section{margin-top:48px}
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

JS = r"""
(function () {
  'use strict';
  var app = document.getElementById('app');
  var KEY = 'mentor-guide:' + app.getAttribute('data-key');
  var mem = [];
  function load() { try { var v = JSON.parse(localStorage.getItem(KEY) || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return mem; } }
  function save(v) { mem = v; try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} }

  /* tabs (WAI-ARIA tabs pattern, roving tabindex) */
  var tabs = Array.prototype.slice.call(document.querySelectorAll('[role="tab"]'));
  function show(name, focus) {
    tabs.forEach(function (t) {
      var on = t.getAttribute('data-panel') === name;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      var p = document.getElementById('panel-' + t.getAttribute('data-panel'));
      if (p) p.hidden = !on;
      if (on && focus) t.focus();
    });
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
  Array.prototype.forEach.call(document.querySelectorAll('[data-goto]'), function (b) {
    b.addEventListener('click', function () { show(b.getAttribute('data-goto')); });
  });
  var start = (location.hash || '').slice(1);
  var names = tabs.map(function (t) { return t.getAttribute('data-panel'); });
  show(names.indexOf(start) > -1 ? start : names[0]);

  /* progress */
  var boxes = Array.prototype.slice.call(document.querySelectorAll('.chk'));
  var bar = document.getElementById('bar'), label = document.getElementById('prog-text'),
      meter = document.getElementById('meter');
  function render() {
    var done = boxes.filter(function (b) { return b.checked; }).length, total = boxes.length;
    boxes.forEach(function (b) { b.closest('.step').classList.toggle('done', b.checked); });
    if (!total) return;
    var pct = Math.round(done / total * 100);
    if (bar) bar.style.width = pct + '%';
    if (meter) meter.setAttribute('aria-valuenow', String(pct));
    if (label) label.textContent = done === total ? 'All ' + total + ' steps done' : done + ' of ' + total + ' steps';
  }
  var saved = load();
  boxes.forEach(function (b, i) {
    b.checked = saved.indexOf(i) > -1;
    b.addEventListener('change', function () {
      save(boxes.map(function (x, j) { return x.checked ? j : -1; }).filter(function (j) { return j > -1; }));
      render();
    });
  });
  var reset = document.getElementById('reset');
  if (reset) reset.addEventListener('click', function () {
    boxes.forEach(function (b) { b.checked = false; }); save([]); render();
  });
  render();

  /* video: facade, then iframe; timestamps restart the iframe at `start` */
  function play(player, secs) {
    var id = player.getAttribute('data-vid');
    var f = document.createElement('iframe');
    f.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) +
      '?autoplay=1&rel=0&modestbranding=1&start=' + (secs || 0);
    f.title = player.getAttribute('data-title') || 'Video';
    f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    f.setAttribute('allowfullscreen', '');
    f.referrerPolicy = 'strict-origin-when-cross-origin';
    player.textContent = '';
    player.appendChild(f);
  }
  document.addEventListener('click', function (ev) {
    var t = ev.target, link = t.closest && t.closest('[data-seek]'), face = t.closest && t.closest('.facade');
    if (link) {
      var card = link.closest('.video'), p = card && card.querySelector('.player');
      if (p) { ev.preventDefault(); play(p, parseInt(link.getAttribute('data-seek'), 10) || 0);
        p.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
    } else if (face) { play(face.parentNode, 0); }
  });
  document.addEventListener('error', function (ev) {
    if (ev.target && ev.target.classList && ev.target.classList.contains('facade-img')) ev.target.style.display = 'none';
  }, true);
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

    ctx = {
        "topic": topic,
        "goal": txt(inputs.get("goal"), 500),
        "level": level,
        "lessons": norm_lessons(inputs.get("key_lessons"), warn),
        "quotes": norm_quotes(inputs.get("expert_quotes"), warn),
        "steps": norm_steps(inputs.get("action_steps"), warn),
        "videos": norm_videos(inputs.get("videos"), warn),
        "web": norm_web(inputs.get("web_sources"), warn),
    }

    key = hashlib.sha256(("\x1f".join([topic] + [s["title"] for s in ctx["steps"]])).encode("utf-8")).hexdigest()[:16]

    tabs = [("overview", "Overview", render_overview(ctx))]
    if ctx["lessons"] or ctx["quotes"]:
        tabs.append(("lessons", "Key lessons", render_lessons(ctx)))
    if ctx["steps"]:
        tabs.append(("action", "Action plan", render_action(ctx)))
    if ctx["videos"] or ctx["web"]:
        tabs.append(("resources", "Resources", render_resources(ctx)))
    if len(tabs) == 1:
        warn("no lessons, steps or resources were provided; only the overview was built")

    tab_html = "".join(
        f'<button type="button" class="tab" role="tab" id="tab-{n}" data-panel="{n}" '
        f'aria-controls="panel-{n}" aria-selected="{"true" if i == 0 else "false"}" '
        f'tabindex="{0 if i == 0 else -1}">{label}</button>'
        for i, (n, label, _) in enumerate(tabs)
    )
    progress = ""
    if ctx["steps"]:
        progress = (
            '<div class="progress"><div class="track" id="meter" role="progressbar" aria-label="Action plan progress" '
            'aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="bar" id="bar"></div></div>'
            f'<span id="prog-text" aria-live="polite">0 of {len(ctx["steps"])} steps</span></div>'
        )

    fonts = FONT_LINKS if WEB_FONTS else ""
    csp = CSP if WEB_FONTS else CSP.replace(" https://fonts.googleapis.com", "").replace("font-src https://fonts.gstatic.com; ", "")
    desc = esc(clip(ctx["goal"] or f"Interactive mentor guide for {topic}", 160))

    doc = (
        f'<!DOCTYPE html><html lang="en" style="--h:{topic_hue(topic)}"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{esc(csp)}">'
        f'<meta name="description" content="{desc}"><meta name="color-scheme" content="light dark">'
        f'<title>{esc(topic)}: mentor guide</title>{fonts}<style>{CSS}</style></head>'
        f'<body><div id="app" data-key="{key}">'
        f'<nav class="nav" aria-label="Guide sections"><div class="nav-in"><div class="tabs" role="tablist">{tab_html}</div>{progress}</div></nav>'
        f'<main>{"".join(p for _, _, p in tabs)}</main></div>'
        f'<script>{JS}</script></body></html>'
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
        summary = "Mentor guide app built successfully"
        if warnings:
            summary += f" with {len(warnings)} input warning(s)"
        return {"html_app": html_app, "summary": summary, "warnings": warnings}
    except Exception as exc:  # last-resort guard: always return a renderable page
        return {
            "html_app": error_page(f"{type(exc).__name__}: {exc}"),
            "summary": f"Mentor guide build failed: {type(exc).__name__}",
            "warnings": warnings + [str(exc)],
        }


# -- Self-test (python build_app.py) ------------------------------------------

def _selftest() -> None:
    hostile = {
        "topic": '<img src=x onerror=alert(1)> Guitar',
        "depth": "wizard",
        "key_lessons": ["plain string lesson", {"title": "<b>x</b>", "desc": "d", "tips": "- one\n- two"}, 42, None],
        "expert_quotes": ["just text", {"text": "q", "author": "A"}, {"author": "no text"}],
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
    assert "failed" not in out["summary"]
    for bad in (None, [], "not json", {}):
        assert run(bad)["html_app"], "must always return a page"
    print("self-test ok;", len(out["warnings"]), "warnings;", len(h), "bytes")


try:
    _INPUTS = inputs  # injected by SkillExecutor
except NameError:
    _INPUTS = None

if _INPUTS is not None:
    result = run(_INPUTS)
elif __name__ == "__main__":
    _selftest()
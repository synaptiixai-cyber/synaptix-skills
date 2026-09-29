"""
build_app.py — Mentor Guide HTML App Builder  (v3.0 — Studio Grade)
Executed by SkillExecutor via run_script().
stdlib only: json, re, html, hashlib

Design principles (Anthropic frontend-design skill):
  - Distinctive visual identity specific to the topic, not template defaults
  - Typography as personality: Inter + Playfair Display, deliberate type scale
  - Motion answers actions: single orchestrated load sequence only
  - Structural devices encode information, not decoration
  - No scattered hover-on-everything; no ALL CAPS eyebrows
  - Hero opens with the most characteristic element for this subject
  - Real content throughout, not "Lorem ipsum" placeholders
  - Line lengths < 80 chars, generous line-height

Output: Complete self-contained HTML SPA wrapped in:
    <!-- synaptix-html-app -->...<!-- /synaptix-html-app -->
"""
import json
import re
import html as html_lib
import hashlib

# ── Helpers ───────────────────────────────────────────────────────────────────

def e(text):
    if text is None:
        return ""
    return html_lib.escape(str(text))

def safe_url(url):
    url = str(url or "")
    if re.match(r'^(javascript|data|vbscript):', url, re.IGNORECASE):
        return "#"
    return url

def youtube_id(url):
    m = re.search(r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})', str(url))
    return m.group(1) if m else None

def ts_to_seconds(ts):
    """'14:55' → '895' for YouTube ?t= param"""
    parts = str(ts).split(":")
    try:
        if len(parts) == 2:
            return str(int(parts[0]) * 60 + int(parts[1]))
        if len(parts) == 3:
            return str(int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))
    except Exception:
        pass
    return "0"

def topic_hue(topic):
    """Derive a stable accent hue from the topic string for visual distinctiveness."""
    h = int(hashlib.md5(topic.encode()).hexdigest(), 16)
    # Avoid the generic indigo/purple (250-290) and lime/yellow (50-80)
    # Distribute across: red 0, orange 22, teal 175, sky 200, rose 340
    palette = [4, 22, 175, 200, 222, 258, 340]
    return palette[h % len(palette)]

def hsl(hue, s, l):
    return f"hsl({hue},{s}%,{l}%)"

# ── CSS & Fonts ───────────────────────────────────────────────────────────────

def build_css(hue):
    a  = hsl(hue, 78, 62)   # accent
    a2 = hsl(hue, 78, 42)   # accent dark
    a3 = hsl(hue, 78, 18)   # accent bg tint
    a4 = hsl(hue, 40, 30)   # accent muted border

    return f"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,700;1,500&display=swap');

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --accent:     {a};
  --accent-dk:  {a2};
  --accent-bg:  {a3};
  --accent-bd:  {a4};
  --bg:         #080c14;
  --surface:    #0d1117;
  --surface2:   #161b27;
  --border:     #1e2736;
  --text:       #e6eaf2;
  --muted:      #6b7a96;
  --subtle:     #2a3548;
  --font-body:  'Inter', system-ui, -apple-system, sans-serif;
  --font-display: 'Playfair Display', Georgia, serif;
}}

html {{ scroll-behavior: smooth; }}

body {{
  font-family: var(--font-body);
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  font-size: 15px;
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
}}

/* ── Sticky nav ─────────────────────────────────────────── */
#nav {{
  position: sticky; top: 0; z-index: 200;
  background: rgba(8,12,20,0.88);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border-bottom: 1px solid var(--border);
}}
#nav-inner {{
  max-width: 900px; margin: 0 auto;
  display: flex; align-items: stretch;
  overflow-x: auto; scrollbar-width: none; gap: 0;
}}
#nav-inner::-webkit-scrollbar {{ display: none; }}

.nav-btn {{
  font-family: var(--font-body);
  font-size: 13px; font-weight: 500;
  color: var(--muted);
  padding: 14px 20px;
  border: none; background: none;
  border-bottom: 2px solid transparent;
  cursor: pointer; white-space: nowrap;
  transition: color 0.18s, border-color 0.18s;
  letter-spacing: 0.01em;
  outline-offset: -2px;
}}
.nav-btn:hover {{ color: var(--text); }}
.nav-btn.active {{
  color: var(--accent);
  border-bottom-color: var(--accent);
}}

/* ── Progress pill ──────────────────────────────────────── */
#progress-pill {{
  margin-left: auto;
  display: flex; align-items: center; gap: 10px;
  padding: 0 16px; flex-shrink: 0;
}}
#progress-pill .pill-track {{
  width: 80px; height: 4px;
  background: var(--subtle);
  border-radius: 4px; overflow: hidden;
}}
#prog-bar {{
  height: 100%; width: 0%;
  background: var(--accent);
  border-radius: 4px;
  transition: width 0.4s cubic-bezier(.4,0,.2,1);
}}
#prog-label {{
  font-size: 11px; font-weight: 600;
  color: var(--muted); white-space: nowrap;
}}

/* ── Page shell ─────────────────────────────────────────── */
#shell {{
  max-width: 900px; margin: 0 auto;
  padding: 40px 20px 80px;
}}

/* ── Tab panels ─────────────────────────────────────────── */
.panel {{ display: none; }}
.panel.visible {{
  display: block;
  animation: panelIn 0.22s cubic-bezier(.4,0,.2,1);
}}
@keyframes panelIn {{
  from {{ opacity: 0; transform: translateY(10px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}

/* ── Hero (overview) ────────────────────────────────────── */
#hero {{
  border-radius: 20px;
  background: linear-gradient(135deg, var(--accent-bg) 0%, var(--surface) 60%);
  border: 1px solid var(--accent-bd);
  padding: 44px 40px 36px;
  margin-bottom: 32px;
  position: relative; overflow: hidden;
}}
#hero::before {{
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 60% 80% at 90% 20%, {hsl(hue,70,25)} 0%, transparent 70%);
  pointer-events: none;
}}
#hero-eyebrow {{
  font-size: 11px; font-weight: 600;
  color: var(--accent); letter-spacing: 0.08em;
  margin-bottom: 14px;
  display: flex; align-items: center; gap: 8px;
}}
#hero-eyebrow::after {{
  content: '';
  flex: 1; max-width: 48px;
  height: 1px; background: var(--accent-bd);
}}
#hero h1 {{
  font-family: var(--font-display);
  font-size: clamp(26px, 4vw, 40px);
  font-weight: 700; line-height: 1.2;
  color: var(--text); margin-bottom: 16px;
  max-width: 560px;
}}
#hero-goal {{
  font-size: 15px; color: var(--muted);
  line-height: 1.65; max-width: 520px;
  margin-bottom: 24px;
}}
.depth-tag {{
  display: inline-block;
  font-size: 11px; font-weight: 600;
  padding: 4px 12px; border-radius: 99px;
  border: 1px solid var(--accent-bd);
  color: var(--accent); background: var(--accent-bg);
  letter-spacing: 0.04em;
}}

/* ── Opening quote ──────────────────────────────────────── */
.hero-quote {{
  margin-top: 28px; padding-top: 24px;
  border-top: 1px solid var(--border);
}}
.hero-quote blockquote {{
  font-family: var(--font-display);
  font-style: italic; font-size: 17px;
  color: var(--text); line-height: 1.6;
  max-width: 500px;
}}
.hero-quote cite {{
  display: block; margin-top: 10px;
  font-family: var(--font-body);
  font-style: normal; font-size: 12px;
  color: var(--muted); font-weight: 500;
}}

/* ── Lesson cards ───────────────────────────────────────── */
.lessons-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 14px;
}}
.lesson-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px; padding: 22px 24px;
  display: flex; gap: 18px; align-items: flex-start;
  transition: border-color 0.18s, background 0.18s;
  cursor: default;
}}
.lesson-card:hover {{
  border-color: var(--accent-bd);
  background: var(--surface2);
}}
.lesson-icon {{
  width: 36px; height: 36px; flex-shrink: 0;
  background: var(--accent-bg);
  border-radius: 10px;
  display: flex; align-items: center;
  justify-content: center;
  font-size: 17px; margin-top: 1px;
}}
.lesson-text {{
  font-size: 14px; line-height: 1.65;
  color: #c5cde0; max-width: 72ch;
}}

/* ── Quotes aside ───────────────────────────────────────── */
.quote-rail {{
  margin-top: 32px;
  display: flex; flex-direction: column; gap: 14px;
}}
.quote-card {{
  padding: 18px 22px;
  border-left: 3px solid var(--accent);
  background: var(--surface);
  border-radius: 0 12px 12px 0;
}}
.quote-card blockquote {{
  font-family: var(--font-display);
  font-style: italic; font-size: 15px;
  color: var(--text); line-height: 1.6;
}}
.quote-card cite {{
  display: block; margin-top: 8px;
  font-style: normal; font-size: 12px;
  color: var(--muted); font-weight: 500;
}}

/* ── Action plan ────────────────────────────────────────── */
.steps-list {{
  display: flex; flex-direction: column; gap: 10px;
}}
.step-row {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px; padding: 18px 22px;
  display: flex; gap: 18px; align-items: flex-start;
  transition: border-color 0.18s, opacity 0.25s;
}}
.step-row.done {{
  opacity: 0.5;
  border-color: var(--accent-bd) !important;
}}
.step-row.done .step-title {{
  text-decoration: line-through;
  color: var(--muted) !important;
}}
.step-checkbox {{
  width: 20px; height: 20px;
  accent-color: var(--accent);
  cursor: pointer; flex-shrink: 0;
  margin-top: 2px;
}}
.step-meta {{
  display: flex; align-items: center;
  gap: 10px; margin-bottom: 6px;
}}
.step-counter {{
  font-size: 11px; font-weight: 700;
  color: var(--accent); letter-spacing: 0.04em;
}}
.step-duration {{
  font-size: 11px; color: var(--muted);
}}
.step-title {{
  font-size: 15px; font-weight: 600;
  color: var(--text); line-height: 1.35;
  margin-bottom: 6px;
  transition: color 0.18s;
}}
.step-desc {{
  font-size: 13px; color: var(--muted);
  line-height: 1.65; max-width: 68ch;
}}

/* ── Resources ──────────────────────────────────────────── */
.section-label {{
  font-size: 12px; font-weight: 600;
  color: var(--muted); letter-spacing: 0.04em;
  margin-bottom: 16px;
}}
.video-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 16px; margin-bottom: 36px;
}}
.video-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px; overflow: hidden;
  display: flex; flex-direction: column;
  transition: border-color 0.18s, transform 0.18s;
}}
.video-card:hover {{
  border-color: var(--accent-bd);
  transform: translateY(-2px);
}}
.video-thumb {{
  aspect-ratio: 16/9; overflow: hidden;
  background: var(--surface2);
  position: relative;
}}
.video-thumb img {{
  width: 100%; height: 100%;
  object-fit: cover; display: block;
  transition: transform 0.3s;
}}
.video-card:hover .video-thumb img {{ transform: scale(1.03); }}
.play-badge {{
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.35);
  opacity: 0; transition: opacity 0.2s;
}}
.video-card:hover .play-badge {{ opacity: 1; }}
.play-badge svg {{
  width: 44px; height: 44px;
  fill: white; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.5));
}}
.video-thumb-fallback {{
  width: 100%; aspect-ratio: 16/9;
  background: var(--surface2);
  display: flex; align-items: center; justify-content: center;
  font-size: 36px; color: var(--muted);
}}
.video-info {{ padding: 14px 16px; flex: 1; }}
.video-title {{
  font-size: 14px; font-weight: 600;
  color: var(--text); line-height: 1.4;
  margin-bottom: 4px; text-decoration: none;
  display: block;
}}
.video-title:hover {{ color: var(--accent); }}
.video-channel {{
  font-size: 12px; color: var(--muted); margin-bottom: 12px;
}}
.ts-list {{ display: flex; flex-direction: column; gap: 2px; }}
.ts-link {{
  display: flex; gap: 10px; align-items: center;
  padding: 5px 8px; border-radius: 7px;
  text-decoration: none;
  transition: background 0.14s;
}}
.ts-link:hover {{ background: var(--surface2); }}
.ts-time {{
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px; font-weight: 700;
  color: var(--accent); min-width: 38px;
}}
.ts-label {{ font-size: 12px; color: var(--muted); line-height: 1.4; }}

.web-links {{ display: flex; flex-direction: column; gap: 8px; }}
.web-link {{
  display: flex; align-items: center; gap: 14px;
  padding: 14px 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px; text-decoration: none;
  transition: border-color 0.18s;
}}
.web-link:hover {{ border-color: var(--accent-bd); }}
.web-link-icon {{
  width: 32px; height: 32px; flex-shrink: 0;
  background: var(--accent-bg);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px;
}}
.web-link-title {{
  font-size: 14px; color: var(--text);
  font-weight: 500; flex: 1;
  line-height: 1.4;
}}
.web-link-arrow {{
  font-size: 14px; color: var(--subtle); flex-shrink: 0;
}}

/* ── Overview stats row ─────────────────────────────────── */
.stats-row {{
  display: flex; gap: 10px; flex-wrap: wrap;
  margin-bottom: 32px;
}}
.stat-chip {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 16px;
  display: flex; flex-direction: column; gap: 2px;
}}
.stat-num {{
  font-family: var(--font-display);
  font-size: 22px; font-weight: 700;
  color: var(--text); line-height: 1;
}}
.stat-desc {{ font-size: 11px; color: var(--muted); }}

/* ── Responsive ─────────────────────────────────────────── */
@media (max-width: 600px) {{
  #hero {{ padding: 28px 20px 24px; }}
  #hero h1 {{ font-size: 24px; }}
  .lessons-grid {{ grid-template-columns: 1fr; }}
  .video-grid {{ grid-template-columns: 1fr; }}
  #progress-pill {{ display: none; }}
}}

/* ── Scrollbar ──────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--subtle); border-radius: 4px; }}
"""

# ── Section builders ──────────────────────────────────────────────────────────

def build_overview(topic, goal, depth, key_lessons, expert_quotes, videos, action_steps):
    depth_labels = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}
    depth_label = depth_labels.get(str(depth).lower(), "Beginner")

    hero_quote = ""
    if expert_quotes:
        q = expert_quotes[0]
        hero_quote = f"""
      <div class="hero-quote">
        <blockquote>"{e(q.get('text',''))}"</blockquote>
        <cite>— {e(q.get('author',''))}</cite>
      </div>"""

    stats_row = f"""
    <div class="stats-row">
      <div class="stat-chip">
        <span class="stat-num">{len(key_lessons)}</span>
        <span class="stat-desc">key insights</span>
      </div>
      <div class="stat-chip">
        <span class="stat-num">{len(action_steps)}</span>
        <span class="stat-desc">action steps</span>
      </div>
      <div class="stat-chip">
        <span class="stat-num">{len(videos)}</span>
        <span class="stat-desc">video sources</span>
      </div>
    </div>""" if (key_lessons or action_steps or videos) else ""

    lessons_preview = ""
    if key_lessons:
        icons = ["◆", "◇", "▸", "◈", "◉", "◎"]
        items = "".join(
            f'<li style="padding:9px 0;border-bottom:1px solid var(--border);'
            f'color:var(--muted);font-size:13px;display:flex;gap:10px;align-items:flex-start;">'
            f'<span style="color:var(--accent);margin-top:1px;">{icons[i % len(icons)]}</span>'
            f'<span>{e(l)}</span></li>'
            for i, l in enumerate(key_lessons[:4])
        )
        lessons_preview = f"""
    <div style="background:var(--surface);border:1px solid var(--border);
                border-radius:14px;padding:20px 24px;margin-bottom:16px;">
      <p style="font-size:12px;font-weight:600;color:var(--muted);
                letter-spacing:0.04em;margin-bottom:12px;">From the research</p>
      <ul style="list-style:none;padding:0;">{items}</ul>
    </div>"""

    return f"""
    <div class="panel visible" id="panel-overview">
      <div id="hero">
        <div id="hero-eyebrow">{e(depth_label)} guide</div>
        <h1>{e(topic)}</h1>
        <p id="hero-goal">{e(goal or "Master this topic and apply it in your daily life.")}</p>
        <span class="depth-tag">{e(depth_label)}</span>
        {hero_quote}
      </div>
      {stats_row}
      {lessons_preview}
    </div>"""


def build_lessons(key_lessons, expert_quotes):
    icons = ["🎯", "💡", "🔑", "⚡", "🧠", "🌱", "🔭", "🛠", "📐", "🌊"]

    cards = ""
    for i, lesson in enumerate(key_lessons or []):
        icon = icons[i % len(icons)]
        cards += f"""
        <div class="lesson-card">
          <div class="lesson-icon">{icon}</div>
          <p class="lesson-text">{e(lesson)}</p>
        </div>"""

    quotes_html = ""
    for q in (expert_quotes or []):
        quotes_html += f"""
        <div class="quote-card">
          <blockquote>"{e(q.get('text',''))}"</blockquote>
          <cite>— {e(q.get('author',''))}</cite>
        </div>"""

    empty = '<p style="color:var(--muted);text-align:center;padding:60px 0;">No insights extracted yet.</p>'

    return f"""
    <div class="panel" id="panel-lessons">
      <div class="lessons-grid">
        {cards or empty}
      </div>
      {f'<div class="quote-rail">{quotes_html}</div>' if quotes_html else ""}
    </div>"""


def build_action_plan(action_steps):
    steps_html = ""
    for i, s in enumerate(action_steps or []):
        n      = s.get("step", i + 1)
        title  = e(s.get("title", ""))
        desc   = e(s.get("description", ""))
        dur    = e(s.get("duration", ""))
        dur_html = f'<span class="step-duration">· {dur}</span>' if dur else ""
        steps_html += f"""
        <div class="step-row" id="step-row-{n}">
          <input type="checkbox" class="step-checkbox" id="chk-{n}"
                 onchange="onCheck(this, 'step-row-{n}')">
          <div style="flex:1;">
            <div class="step-meta">
              <span class="step-counter">Step {n}</span>
              {dur_html}
            </div>
            <p class="step-title" id="step-title-{n}">{title}</p>
            <p class="step-desc">{desc}</p>
          </div>
        </div>"""

    total = len(action_steps or [])
    empty = '<p style="color:var(--muted);text-align:center;padding:60px 0;">No action steps available.</p>'

    return f"""
    <div class="panel" id="panel-action">
      <div class="steps-list">
        {steps_html or empty}
      </div>
    </div>
    <script>var _TOTAL_STEPS = {total};</script>"""


def build_resources(videos, web_sources):
    play_icon = (
        '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>'
    )

    video_cards = ""
    for v in (videos or []):
        url    = safe_url(v.get("url", ""))
        vid_id = youtube_id(url)
        title  = e(v.get("title", "Untitled Video"))
        ch     = e(v.get("channel", ""))
        dur    = e(v.get("duration", ""))

        if vid_id:
            thumb_html = f"""
              <a href="{e(url)}" target="_blank" rel="noopener">
                <img src="https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"
                     alt="{title}" loading="lazy"
                     onerror="this.parentElement.innerHTML='<div class=video-thumb-fallback>▶</div>'">
                <div class="play-badge">{play_icon}</div>
              </a>"""
        else:
            thumb_html = f'<div class="video-thumb-fallback">▶</div>'

        ts_links = ""
        for ts in (v.get("key_timestamps") or []):
            t      = ts.get("time", "")
            label  = ts.get("label", "")
            secs   = ts_to_seconds(t)
            ts_url = f"{url}{'&' if '?' in url else '?'}t={secs}s" if vid_id and t else url
            ts_links += f"""
              <a href="{safe_url(ts_url)}" target="_blank" rel="noopener" class="ts-link">
                <span class="ts-time">{e(t)}</span>
                <span class="ts-label">{e(label)}</span>
              </a>"""

        ts_section = (
            f'<div style="border-top:1px solid var(--border);padding-top:10px;margin-top:10px;">'
            f'<div class="ts-list">{ts_links}</div></div>'
        ) if ts_links else ""

        ch_dur = " · ".join(filter(None, [ch, dur]))

        video_cards += f"""
        <div class="video-card">
          <div class="video-thumb">{thumb_html}</div>
          <div class="video-info">
            <a href="{e(url)}" target="_blank" rel="noopener" class="video-title">{title}</a>
            <p class="video-channel">{e(ch_dur)}</p>
            {ts_section}
          </div>
        </div>"""

    web_html = ""
    for src in (web_sources or []):
        src_title = e(src.get("title", ""))
        src_url   = safe_url(src.get("url", "#"))
        web_html += f"""
        <a href="{e(src_url)}" target="_blank" rel="noopener" class="web-link">
          <div class="web-link-icon">🔗</div>
          <span class="web-link-title">{src_title}</span>
          <span class="web-link-arrow">↗</span>
        </a>"""

    empty = '<p style="color:var(--muted);text-align:center;padding:60px 0;">No resources available.</p>'

    video_section = (
        f'<p class="section-label">Video sources</p>'
        f'<div class="video-grid">{video_cards}</div>'
    ) if video_cards else ""

    web_section = (
        f'<p class="section-label">Further reading</p>'
        f'<div class="web-links">{web_html}</div>'
    ) if web_html else ""

    return f"""
    <div class="panel" id="panel-resources">
      {video_section}
      {web_section}
      {empty if not video_section and not web_section else ""}
    </div>"""


# ── JavaScript ────────────────────────────────────────────────────────────────

JS = """
(function() {
  var panels   = ['overview','lessons','action','resources'];
  var navBtns  = document.querySelectorAll('.nav-btn');
  var TOTAL    = typeof _TOTAL_STEPS !== 'undefined' ? _TOTAL_STEPS : 0;

  function showPanel(name) {
    panels.forEach(function(p) {
      var el = document.getElementById('panel-' + p);
      if (el) { el.classList.remove('visible'); }
    });
    var target = document.getElementById('panel-' + name);
    if (target) {
      // Force reflow to re-trigger animation
      target.classList.remove('visible');
      void target.offsetWidth;
      target.classList.add('visible');
    }
    navBtns.forEach(function(b) {
      b.classList.toggle('active', b.dataset.panel === name);
    });
  }

  // Wire nav buttons
  navBtns.forEach(function(btn) {
    btn.addEventListener('click', function() { showPanel(btn.dataset.panel); });
  });

  // Checkbox → progress
  window.onCheck = function(checkbox, rowId) {
    var row = document.getElementById(rowId);
    if (row) row.classList.toggle('done', checkbox.checked);
    updateProgress();
  };

  function updateProgress() {
    var boxes = document.querySelectorAll('.step-checkbox');
    var done  = 0;
    boxes.forEach(function(b) { if (b.checked) done++; });
    var total = TOTAL || boxes.length || 1;
    var pct   = Math.round((done / total) * 100);
    var bar   = document.getElementById('prog-bar');
    var lbl   = document.getElementById('prog-label');
    if (bar) bar.style.width = pct + '%';
    if (lbl) lbl.textContent = done + '/' + total;
  }

  // Init
  showPanel('overview');
  updateProgress();
})();
"""

# ── Main assembly ─────────────────────────────────────────────────────────────

def main(inputs):
    topic         = str(inputs.get("topic", "Your Topic"))
    goal          = str(inputs.get("goal", ""))
    depth         = str(inputs.get("depth", "beginner")).lower()
    videos        = inputs.get("videos", []) or []
    key_lessons   = inputs.get("key_lessons", []) or []
    action_steps  = inputs.get("action_steps", []) or []
    expert_quotes = inputs.get("expert_quotes", []) or []
    web_sources   = inputs.get("web_sources", []) or []

    hue = topic_hue(topic)
    css = build_css(hue)

    panel_overview  = build_overview(topic, goal, depth, key_lessons, expert_quotes, videos, action_steps)
    panel_lessons   = build_lessons(key_lessons, expert_quotes)
    panel_action    = build_action_plan(action_steps)
    panel_resources = build_resources(videos, web_sources)

    page = f"""<!-- synaptix-html-app -->
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Interactive mentor guide for {e(topic)}">
<title>{e(topic)} — Mentor Guide</title>
<style>{css}</style>
</head>
<body>

<nav id="nav">
  <div id="nav-inner">
    <button class="nav-btn active" data-panel="overview">Overview</button>
    <button class="nav-btn" data-panel="lessons">Key Lessons</button>
    <button class="nav-btn" data-panel="action">Action Plan</button>
    <button class="nav-btn" data-panel="resources">Resources</button>
    <div id="progress-pill">
      <div class="pill-track"><div id="prog-bar"></div></div>
      <span id="prog-label">0/{len(action_steps)}</span>
    </div>
  </div>
</nav>

<div id="shell">
  {panel_overview}
  {panel_lessons}
  {panel_action}
  {panel_resources}
</div>

<script>{JS}</script>
</body>
</html>
<!-- /synaptix-html-app -->"""

    return page


# Entry point called by SkillScriptRunner
result = main(inputs)

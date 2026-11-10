"""SVG & self-contained HTML5 renderer with 5-act CSS choreography and static mode."""

import html
import re
from typing import Any, Dict, List, Tuple

ID_SAFE_RE = re.compile(r"[^a-z0-9-]+")
MAX_TOTAL_DURATION_S = 8.0


def esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def safe_id(raw_id: str) -> str:
    cleaned = ID_SAFE_RE.sub("-", str(raw_id or "").lower()).strip("-")
    return cleaned or "el"


def render_text_lines(
    elem_id: str,
    lines: List[str],
    x: float,
    y: float,
    font_size: float,
    line_height: float,
    fill: str,
    weight: int = 400,
    anchor: str = "start",
    cls: str = "reveal",
    delay_s: float = 0.0,
    letter_spacing: str = "",
) -> str:
    """Render wrapped SVG <text> with <tspan> lines where y is top of text box."""
    if not lines:
        return ""
    sid = safe_id(elem_id)
    cls_attr = f' class="{esc(cls)}"' if cls else ""
    style_parts: List[str] = []
    if cls:
        style_parts.append(f"--d:{delay_s:.2f}s")
    if letter_spacing:
        style_parts.append(f"letter-spacing:{letter_spacing}")
    style_attr = f' style="{";".join(style_parts)}"' if style_parts else ""

    rx = round(x, 2)
    # First baseline positioned ~0.84em below top edge of box
    first_y = round(y + font_size * 0.84, 2)
    tspans: List[str] = []
    for idx, ln in enumerate(lines):
        ly = round(first_y + idx * line_height, 2)
        tspans.append(f'<tspan x="{rx}" y="{ly}">{esc(ln)}</tspan>')

    return (
        f'<text id="{sid}"{cls_attr}{style_attr} x="{rx}" y="{first_y}" '
        f'font-size="{round(font_size, 1)}" font-weight="{weight}" '
        f'fill="{esc(fill)}" text-anchor="{esc(anchor)}">'
        + "".join(tspans)
        + "</text>"
    )


def assign_schedule(
    elements: List[Dict[str, Any]],
    step_ms: int,
) -> Tuple[List[Dict[str, Any]], float]:
    """Compute 5-act staggered delays (--d) capped cleanly under 8.0 seconds."""
    # Acts: 1=Establish, 2=Build, 3=Connect, 4=Flow, 5=Resolve
    by_act: Dict[int, List[Dict[str, Any]]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    for el in elements:
        act = int(el.get("act", 2))
        if act < 1 or act > 5:
            act = 2
        by_act[act].append(el)

    total_animated = sum(len(by_act[a]) for a in (2, 3, 4, 5))
    raw_step_s = max(0.03, step_ms / 1000.0)
    # Base anim duration per item is ~0.55s; cap total timeline <= 8.0s
    if total_animated > 0:
        max_allowed_step = max(0.025, (MAX_TOTAL_DURATION_S - 1.4) / max(1, total_animated))
        step_s = min(raw_step_s, max_allowed_step)
    else:
        step_s = raw_step_s

    cursor = 0.0
    scheduled: List[Dict[str, Any]] = []

    # Act 1: Establish (0.0s)
    for el in by_act[1]:
        copy_el = dict(el)
        copy_el["delay_s"] = 0.0
        scheduled.append(copy_el)
    if by_act[1]:
        cursor = 0.16

    # Act 2: Build (nodes, bars, slices, columns)
    for idx, el in enumerate(by_act[2]):
        copy_el = dict(el)
        copy_el["delay_s"] = round(cursor + idx * step_s, 3)
        scheduled.append(copy_el)
    if by_act[2]:
        cursor = cursor + len(by_act[2]) * step_s + 0.18

    # Act 3: Connect (lines, connectors, strokes with pathLength="1")
    for idx, el in enumerate(by_act[3]):
        copy_el = dict(el)
        copy_el["delay_s"] = round(cursor + idx * step_s, 3)
        scheduled.append(copy_el)
    if by_act[3]:
        cursor = cursor + len(by_act[3]) * step_s + 0.20

    # Act 4: Flow (moving dots along connectors for process, cycle, hub)
    for idx, el in enumerate(by_act[4]):
        copy_el = dict(el)
        copy_el["delay_s"] = round(cursor + idx * (step_s * 1.1), 3)
        scheduled.append(copy_el)
    if by_act[4]:
        cursor = cursor + len(by_act[4]) * (step_s * 1.1) + 0.22

    # Act 5: Resolve (verdict, captions, footer, source)
    for idx, el in enumerate(by_act[5]):
        copy_el = dict(el)
        copy_el["delay_s"] = round(cursor + idx * (step_s * 0.8), 3)
        scheduled.append(copy_el)
    if by_act[5]:
        cursor = cursor + len(by_act[5]) * (step_s * 0.8) + 0.50
    else:
        cursor = cursor + 0.55

    duration_s = round(min(MAX_TOTAL_DURATION_S, max(1.2, cursor)), 2)
    return scheduled, duration_s


def render_element_svg(
    el: Dict[str, Any],
    icons_mod: Any,
) -> str:
    kind = el["type"]
    delay_s = float(el.get("delay_s", 0.0))
    sid = safe_id(el.get("id", kind))
    cls = el.get("anim", "reveal")

    if kind == "raw":
        return el["svg"].replace("__DELAY__", f"{delay_s:.2f}s")

    if kind == "rect":
        cls_attr = f' class="{esc(cls)}" style="--d:{delay_s:.2f}s"' if cls else ""
        rx = round(float(el.get("rx", 0.0)), 1)
        stroke = el.get("stroke", "none")
        sw = el.get("stroke_width", 0)
        opacity = el.get("opacity", 1.0)
        op_attr = f' opacity="{round(float(opacity), 3)}"' if opacity != 1.0 else ""
        origin = el.get("origin")
        if origin and cls:
            cls_attr = f' class="{esc(cls)}" style="--d:{delay_s:.2f}s;transform-origin:{esc(origin)}"'
        return (
            f'<rect id="{sid}"{cls_attr} x="{round(el["x"], 2)}" y="{round(el["y"], 2)}" '
            f'width="{round(el["w"], 2)}" height="{round(el["h"], 2)}" rx="{rx}" '
            f'fill="{esc(el.get("fill", "none"))}" stroke="{esc(stroke)}" '
            f'stroke-width="{sw}"{op_attr}/>'
        )

    if kind == "circle":
        cls_attr = f' class="{esc(cls)}" style="--d:{delay_s:.2f}s"' if cls else ""
        stroke = el.get("stroke", "none")
        sw = el.get("stroke_width", 0)
        return (
            f'<circle id="{sid}"{cls_attr} cx="{round(el["cx"], 2)}" cy="{round(el["cy"], 2)}" '
            f'r="{round(el["r"], 2)}" fill="{esc(el.get("fill", "none"))}" '
            f'stroke="{esc(stroke)}" stroke-width="{sw}"/>'
        )

    if kind == "line":
        cls_attr = f' class="{esc(cls)}" style="--d:{delay_s:.2f}s"' if cls else ""
        dash = f' stroke-dasharray="{esc(el["dash"])}"' if el.get("dash") else ""
        pl = ' pathLength="1"' if cls == "draw" else ""
        return (
            f'<line id="{sid}"{cls_attr}{pl} x1="{round(el["x1"], 2)}" y1="{round(el["y1"], 2)}" '
            f'x2="{round(el["x2"], 2)}" y2="{round(el["y2"], 2)}" '
            f'stroke="{esc(el["stroke"])}" stroke-width="{el.get("stroke_width", 2)}" '
            f'stroke-linecap="round"{dash}/>'
        )

    if kind == "path":
        cls_attr = f' class="{esc(cls)}" style="--d:{delay_s:.2f}s"' if cls else ""
        pl = ' pathLength="1"' if cls == "draw" else ""
        fill = el.get("fill", "none")
        stroke = el.get("stroke", "none")
        sw = el.get("stroke_width", 2)
        marker = f' marker-end="url(#{esc(el["marker_end"])})"' if el.get("marker_end") else ""
        origin = el.get("origin")
        if origin and cls:
            cls_attr = f' class="{esc(cls)}" style="--d:{delay_s:.2f}s;transform-origin:{esc(origin)}"'
        return (
            f'<path id="{sid}"{cls_attr}{pl} d="{esc(el["d"])}" '
            f'fill="{esc(fill)}" stroke="{esc(stroke)}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"{marker}/>'
        )

    if kind == "flow_dot":
        path_d = esc(el["d"])
        r = round(float(el.get("r", 4.5)), 1)
        fill = esc(el["fill"])
        return (
            f'<circle id="{sid}" class="flow-dot" r="{r}" fill="{fill}" '
            f'style="--d:{delay_s:.2f}s;offset-path:path(\'{path_d}\')"/>'
        )

    if kind == "icon":
        return icons_mod.render_icon(
            el["icon"],
            el["x"],
            el["y"],
            el["size"],
            el["stroke"],
            elem_id=sid,
            cls=cls,
            delay_s=delay_s,
        )

    if kind == "text":
        return render_text_lines(
            elem_id=sid,
            lines=el["lines"],
            x=el["x"],
            y=el["y"],
            font_size=el["font_size"],
            line_height=el["line_height"],
            fill=el["fill"],
            weight=el.get("weight", 400),
            anchor=el.get("anchor", "start"),
            cls=cls,
            delay_s=delay_s,
            letter_spacing=el.get("letter_spacing", ""),
        )

    return ""


def build_chrome_elements(
    spec: Dict[str, Any],
    chrome: Dict[str, Any],
    theme: Dict[str, Any],
) -> List[Dict[str, Any]]:
    elems: List[Dict[str, Any]] = []
    w = chrome["width"]
    h = chrome["height"]
    m = chrome["margin"]

    # Background canvas
    elems.append({
        "id": "frame-bg",
        "type": "rect",
        "act": 1,
        "anim": "",
        "x": 0,
        "y": 0,
        "w": w,
        "h": h,
        "rx": 0,
        "fill": theme["bg"],
    })

    if chrome["eyebrow_lines"]:
        elems.append({
            "id": "header-eyebrow",
            "type": "text",
            "act": 1,
            "anim": "reveal",
            "lines": chrome["eyebrow_lines"],
            "x": m,
            "y": chrome["eyebrow_y"],
            "font_size": 13,
            "line_height": 17,
            "fill": theme["accent"][0],
            "weight": 700,
            "letter_spacing": "0.08em",
        })

    if chrome["title_lines"]:
        elems.append({
            "id": "header-title",
            "type": "text",
            "act": 1,
            "anim": "reveal",
            "lines": chrome["title_lines"],
            "x": m,
            "y": chrome["title_y"],
            "font_size": chrome["title_font"],
            "line_height": chrome["title_line_h"],
            "fill": theme["ink"],
            "weight": 750,
        })

    if chrome["footer_lines"]:
        elems.append({
            "id": "footer-source",
            "type": "text",
            "act": 5,
            "anim": "reveal",
            "lines": chrome["footer_lines"],
            "x": m,
            "y": chrome["footer_y"],
            "font_size": chrome["footer_font"],
            "line_height": round(chrome["footer_font"] * 1.28, 2),
            "fill": theme["muted"],
            "weight": 500,
        })

    if chrome["has_badge"]:
        bw = chrome["badge_w"]
        bx = w - m - bw
        by = h - m - 18
        elems.append({
            "id": "badge-pill",
            "type": "rect",
            "act": 5,
            "anim": "reveal",
            "x": bx,
            "y": by,
            "w": bw,
            "h": 26,
            "rx": 13,
            "fill": theme["surface_alt"],
            "stroke": theme["border"],
            "stroke_width": 1,
        })
        elems.append({
            "id": "badge-label",
            "type": "text",
            "act": 5,
            "anim": "reveal",
            "lines": ["ILLUSTRATIVE DATA"],
            "x": bx + bw / 2.0,
            "y": by + 6,
            "font_size": 11,
            "line_height": 14,
            "fill": theme["muted"],
            "weight": 700,
            "anchor": "middle",
            "letter_spacing": "0.06em",
        })

    return elems


def build_svg_and_html(
    spec: Dict[str, Any],
    solved: Dict[str, Any],
    theme: Dict[str, Any],
    icons_mod: Any,
    summary_text: str,
) -> Tuple[str, str, float]:
    """Compile the standalone <svg> and full self-contained HTML5 document."""
    chrome = solved["chrome"]
    w = chrome["width"]
    h = chrome["height"]

    chrome_elems = build_chrome_elements(spec, chrome, theme)
    all_raw = chrome_elems + list(solved["elements"])
    scheduled, duration_s = assign_schedule(all_raw, int(theme["motion"]["step_ms"]))

    defs_svg = (
        "<defs>"
        f'<marker id="arrow-muted" viewBox="0 0 10 10" refX="8" refY="5" '
        f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        f'<path d="M 0 1.5 L 8.5 5 L 0 8.5 z" fill="{esc(theme["muted"])}"/>'
        "</marker>"
        f'<marker id="arrow-accent" viewBox="0 0 10 10" refX="8" refY="5" '
        f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        f'<path d="M 0 1.5 L 8.5 5 L 0 8.5 z" fill="{esc(theme["accent"][0])}"/>'
        "</marker>"
        "</defs>"
    )

    svg_children: List[str] = [
        f'<title>{esc(spec["title"])}</title>',
        f'<desc>{esc(summary_text)}</desc>',
        defs_svg,
    ]
    for el in scheduled:
        rendered = render_element_svg(el, icons_mod)
        if rendered:
            svg_children.append(rendered)

    svg_markup = (
        f'<svg id="scene" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
        f'aria-label="{esc(spec["title"])}">'
        + "".join(svg_children)
        + "</svg>"
    )

    ease = theme["motion"]["ease"]
    css = (
        "*{box-sizing:border-box;margin:0;padding:0}"
        f"html,body{{background:{theme['bg']};color:{theme['ink']};font-family:{theme['font']};"
        "-webkit-font-smoothing:antialiased}"
        ".stage{position:relative;width:100%;max-width:1280px;margin:0 auto;overflow:hidden}"
        "svg#scene{display:block;width:100%;height:auto}"
        ".replay{position:absolute;top:12px;right:12px;padding:6px 12px;border-radius:999px;"
        f"border:1px solid {theme['border']};background:{theme['surface']};color:{theme['muted']};"
        "font:600 12px/1 system-ui,sans-serif;cursor:pointer;opacity:0.78;transition:opacity .15s}"
        f".replay:hover{{opacity:1;color:{theme['ink']}}}"
        "html.static .replay{display:none}"
        ".flow-dot{opacity:0;offset-rotate:0deg}"
        "@media (prefers-reduced-motion:no-preference){"
        f"html:not(.static) .reveal{{animation:rev .52s {ease} var(--d,0s) both}}"
        f"html:not(.static) .bar-grow{{animation:growY .58s {ease} var(--d,0s) both}}"
        f"html:not(.static) .draw{{stroke-dasharray:1;stroke-dashoffset:1;"
        f"animation:drawLine .65s {ease} var(--d,0s) forwards}}"
        f"html:not(.static) .flow-dot{{animation:flowMove .95s {ease} var(--d,0s) both}}"
        "}"
        "@keyframes rev{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}"
        "@keyframes growY{from{opacity:0;transform:scaleY(0)}to{opacity:1;transform:scaleY(1)}}"
        "@keyframes drawLine{to{stroke-dashoffset:0}}"
        "@keyframes flowMove{0%{opacity:0;offset-distance:0%}15%{opacity:1}"
        "85%{opacity:1}100%{opacity:0;offset-distance:100%}}"
    )

    js = (
        'var b=document.getElementById("replay"),r=document.documentElement;'
        'if(b){b.onclick=function(){r.classList.add("static");'
        'void r.offsetWidth;r.classList.remove("static");};}'
    )

    csp = (
        "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
        "img-src data:; base-uri 'none'; form-action 'none'"
    )

    html_doc = (
        "<!doctype html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        f"<title>{esc(spec['title'])}</title>"
        f"<style>{css}</style>"
        "</head>"
        "<body>"
        f'<div class="stage">{svg_markup}'
        '<button id="replay" class="replay" type="button" aria-label="Replay animation">↻ Replay</button>'
        "</div>"
        f"<script>{js}</script>"
        "</body>"
        "</html>"
    )
    return svg_markup, html_doc, duration_s

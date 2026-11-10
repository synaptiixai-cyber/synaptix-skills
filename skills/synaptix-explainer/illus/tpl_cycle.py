"""Template: cycle — repeating orbital loop (3..6 stages) + optional center badge."""

import math
from typing import Any, Dict, List


STAGE_ANGLES = {
    3: (-90.0, 30.0, 150.0),
    4: (-90.0, 0.0, 90.0, 180.0),
    5: (-90.0, -18.0, 54.0, 126.0, 198.0),
    6: (-120.0, -60.0, 0.0, 60.0, 120.0, 180.0),
}


def ellipse_pt(cx: float, cy: float, rx: float, ry: float, deg: float) -> Any:
    rad = math.radians(deg)
    return (cx + rx * math.cos(rad), cy + ry * math.sin(rad))


def build(
    spec: Dict[str, Any],
    chrome: Dict[str, Any],
    theme: Dict[str, Any],
    text_mod: Any,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    rect = chrome["content_rect"]
    f_scale = params["font_scale"]
    g_scale = params["gap_scale"]
    m_ratio = params["measure_ratio"]
    scale_font = params["scale_font"]
    make_box = params["make_box"]

    content = spec["content"]
    stages = content["stages"]
    center_txt = content.get("center", "")
    n = len(stages)
    is_wide = spec["aspect"] == "wide"

    head_font = scale_font("card_title", f_scale) - 1
    body_font = scale_font("label", f_scale)

    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    fits = True
    overflow_path = "content.stages"

    cx = rect["x"] + rect["w"] / 2.0
    cy = rect["y"] + rect["h"] / 2.0

    if is_wide:
        card_w = (260.0 if n <= 4 else 236.0) * (0.92 + 0.08 * g_scale)
        card_h = (122.0 if n <= 4 else 110.0) * (0.92 + 0.08 * g_scale)
    else:
        card_w = (264.0 if n <= 4 else 232.0) * (0.92 + 0.08 * g_scale)
        card_h = (146.0 if n <= 4 else 132.0) * (0.92 + 0.08 * g_scale)

    rx = max(140.0, (rect["w"] - card_w) / 2.0 - 8.0)
    ry = max(110.0, (rect["h"] - card_h) / 2.0 - 6.0)
    if n == 6 and is_wide:
        ry = max(120.0, (rect["h"] - card_h) / 2.0 / 0.866 - 4.0)

    # Subtle inner orbital ring
    ring_rx = max(70.0, rx * 0.62)
    ring_ry = max(60.0, ry * 0.62)

    angles = STAGE_ANGLES.get(n, STAGE_ANGLES[4])

    # Orbital arc arrows (Act 3) & flow dots (Act 4)
    for idx in range(n):
        a1 = angles[idx]
        a2 = angles[(idx + 1) % n]
        if a2 <= a1:
            a2 = a2 + 360.0
        span = a2 - a1
        trim = min(22.0, span * 0.24)
        s_ang = a1 + trim
        e_ang = a2 - trim
        steps_arc = 10
        pts_d: List[str] = []
        for s_i in range(steps_arc + 1):
            ang = s_ang + (e_ang - s_ang) * (s_i / float(steps_arc))
            px, py = ellipse_pt(cx, cy, ring_rx, ring_ry, ang)
            cmd = "M" if s_i == 0 else "L"
            pts_d.append(f"{cmd} {px:.2f} {py:.2f}")
        arc_d = " ".join(pts_d)
        elements.append({
            "id": f"edge-{idx}-{(idx + 1) % n}",
            "type": "path",
            "act": 3,
            "anim": "draw",
            "d": arc_d,
            "stroke": theme["accent"][idx % len(theme["accent"])],
            "stroke_width": 2.5,
            "marker_end": "arrow-muted",
        })
        elements.append({
            "id": f"flow-{idx}",
            "type": "flow_dot",
            "act": 4,
            "d": arc_d,
            "r": 4.2,
            "fill": theme["accent"][idx % len(theme["accent"])],
        })

    # Optional center hub pill
    if center_txt:
        cw = min(200.0, ring_rx * 1.35)
        c_wrap = text_mod.wrap_lines(center_txt, (cw - 28.0) * m_ratio, head_font, True, max_lines=2)
        if not c_wrap["fits"]:
            fits = False
            overflow_path = "content.center"
        ch = max(54.0, c_wrap["height"] + 24.0)
        cbx = cx - cw / 2.0
        cby = cy - ch / 2.0
        boxes.append(make_box("cycle-center", "shape", cbx, cby, cw, ch, "cycle-center", None, "content.center"))
        elements.append({
            "id": "cycle-center",
            "type": "rect",
            "act": 1,
            "anim": "reveal",
            "x": cbx,
            "y": cby,
            "w": cw,
            "h": ch,
            "rx": ch / 2.0,
            "fill": theme["surface_alt"],
            "stroke": theme["accent"][0],
            "stroke_width": 2,
        })
        cty = cy - c_wrap["height"] / 2.0
        boxes.append(make_box("cycle-center-txt", "text", cx - c_wrap["width"] / 2.0, cty, max(20.0, c_wrap["width"]), c_wrap["height"], "cycle-center", "cycle-center", "content.center"))
        elements.append({
            "id": "cycle-center-txt",
            "type": "text",
            "act": 1,
            "anim": "reveal",
            "lines": c_wrap["lines"],
            "x": cx,
            "y": cty,
            "font_size": head_font,
            "line_height": c_wrap["line_height"],
            "fill": theme["ink"],
            "weight": 750,
            "anchor": "middle",
        })

    # Stage cards (Act 2)
    for idx, st in enumerate(stages):
        spath = f"content.stages[{idx}]"
        ang = angles[idx]
        scx, scy = ellipse_pt(cx, cy, rx, ry, ang)
        nx = scx - card_w / 2.0
        ny = scy - card_h / 2.0
        nid = f"node-{idx}"
        color = theme["accent"][idx % len(theme["accent"])]

        boxes.append(make_box(nid, "shape", nx, ny, card_w, card_h, nid, None, spath))
        elements.append({
            "id": nid,
            "type": "rect",
            "act": 2,
            "anim": "reveal",
            "x": nx,
            "y": ny,
            "w": card_w,
            "h": card_h,
            "rx": 14,
            "fill": theme["surface"],
            "stroke": color,
            "stroke_width": 1.8,
        })

        pad = 14.0
        avail_w = (card_w - 2 * pad - 28.0) * m_ratio
        t_wrap = text_mod.wrap_lines(st["title"], avail_w, head_font, True, max_lines=2)
        if not t_wrap["fits"]:
            fits = False
            overflow_path = f"{spath}.title"

        # Small step index circle on top-left
        elements.append({
            "id": f"stage-num-bg-{idx}",
            "type": "circle",
            "act": 2,
            "anim": "reveal",
            "cx": nx + pad + 10.0,
            "cy": ny + pad + 10.0,
            "r": 10.0,
            "fill": color,
        })
        elements.append({
            "id": f"stage-num-{idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": [str(idx + 1)],
            "x": nx + pad + 10.0,
            "y": ny + pad + 3.0,
            "font_size": 12,
            "line_height": 14,
            "fill": "#FFFFFF",
            "weight": 800,
            "anchor": "middle",
        })

        tx = nx + pad + 26.0
        ty = ny + pad
        boxes.append(make_box(f"stage-title-{idx}", "text", tx, ty, max(18.0, t_wrap["width"]), t_wrap["height"], f"{nid}-t", nid, f"{spath}.title"))
        elements.append({
            "id": f"stage-title-{idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": t_wrap["lines"],
            "x": tx,
            "y": ty,
            "font_size": head_font,
            "line_height": t_wrap["line_height"],
            "fill": theme["ink"],
            "weight": 750,
        })

        cur_y = ty + max(22.0, t_wrap["height"]) + 6.0 * g_scale
        detail = st.get("detail", "")
        if detail:
            d_avail = (card_w - 2 * pad) * m_ratio
            d_wrap = text_mod.wrap_lines(detail, d_avail, body_font - 1, False, max_lines=3)
            if not d_wrap["fits"] or (cur_y + d_wrap["height"] > ny + card_h - 8.0):
                fits = False
                overflow_path = f"{spath}.detail"
            boxes.append(make_box(f"stage-detail-{idx}", "text", nx + pad, cur_y, max(18.0, d_wrap["width"]), d_wrap["height"], f"{nid}-d", nid, f"{spath}.detail"))
            elements.append({
                "id": f"stage-detail-{idx}",
                "type": "text",
                "act": 2,
                "anim": "reveal",
                "lines": d_wrap["lines"],
                "x": nx + pad,
                "y": cur_y,
                "font_size": body_font - 1,
                "line_height": d_wrap["line_height"],
                "fill": theme["muted"],
                "weight": 450,
            })

    return {
        "fits": fits,
        "overflow_path": overflow_path,
        "adjusted_path": overflow_path,
        "boxes": boxes,
        "elements": elements,
    }

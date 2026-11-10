"""Template: donut-chart — parts of a whole (2..6 slices) with center label & clean legend."""

import math
from typing import Any, Dict, List


def polar_pt(cx: float, cy: float, r: float, angle_deg: float) -> Any:
    rad = math.radians(angle_deg)
    return (cx + r * math.cos(rad), cy + r * math.sin(rad))


def donut_slice_path(
    cx: float,
    cy: float,
    r_outer: float,
    r_inner: float,
    start_deg: float,
    end_deg: float,
) -> str:
    sweep = end_deg - start_deg
    if sweep >= 359.9:
        end_deg = start_deg + 359.85
        sweep = 359.85
    large = 1 if sweep > 180.0 else 0
    ox1, oy1 = polar_pt(cx, cy, r_outer, start_deg)
    ox2, oy2 = polar_pt(cx, cy, r_outer, end_deg)
    ix2, iy2 = polar_pt(cx, cy, r_inner, end_deg)
    ix1, iy1 = polar_pt(cx, cy, r_inner, start_deg)
    return (
        f"M {ox1:.2f} {oy1:.2f} "
        f"A {r_outer:.2f} {r_outer:.2f} 0 {large} 1 {ox2:.2f} {oy2:.2f} "
        f"L {ix2:.2f} {iy2:.2f} "
        f"A {r_inner:.2f} {r_inner:.2f} 0 {large} 0 {ix1:.2f} {iy1:.2f} Z"
    )


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
    items = content["items"]
    center_label = content.get("center_label", "")
    n = len(items)
    total = sum(float(it["value"]) for it in items)

    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    fits = True
    overflow_path = "content.items"

    is_wide = spec["aspect"] == "wide"
    body_font = scale_font("body", f_scale)
    label_font = scale_font("label", f_scale)

    if is_wide:
        donut_zone_w = rect["w"] * 0.48
        cx = rect["x"] + donut_zone_w * 0.5
        cy = rect["y"] + rect["h"] * 0.5
        r_outer = min(donut_zone_w * 0.44, rect["h"] * 0.45)
        leg_x = rect["x"] + donut_zone_w + 24.0
        leg_w = rect["w"] - donut_zone_w - 24.0
        row_gap = 12.0 * g_scale
        row_h = min(68.0, (rect["h"] - row_gap * (n - 1)) / float(n))
        total_leg_h = n * row_h + (n - 1) * row_gap
        leg_start_y = rect["y"] + (rect["h"] - total_leg_h) / 2.0
    else:
        donut_zone_h = rect["h"] * 0.54
        cx = rect["x"] + rect["w"] * 0.5
        cy = rect["y"] + donut_zone_h * 0.5
        r_outer = min(rect["w"] * 0.34, donut_zone_h * 0.46)
        leg_x = rect["x"]
        leg_w = rect["w"]
        leg_start_y = rect["y"] + donut_zone_h + 20.0
        avail_leg_h = rect["h"] - donut_zone_h - 20.0
        cols = 2
        rows = (n + 1) // 2
        row_gap = 12.0 * g_scale
        row_h = min(74.0, (avail_leg_h - row_gap * max(0, rows - 1)) / float(max(1, rows)))

    r_inner = r_outer * 0.60
    boxes.append(make_box("donut-ring", "shape", cx - r_outer, cy - r_outer, r_outer * 2.0, r_outer * 2.0, "donut-ring", None, "content.items"))

    # Slices (Act 2)
    cur_deg = -90.0
    gap_deg = 1.6 if n > 1 else 0.0
    for idx, it in enumerate(items):
        share = float(it["value"]) / total
        span = share * 360.0
        s_deg = cur_deg + gap_deg / 2.0
        e_deg = cur_deg + max(gap_deg + 0.5, span - gap_deg / 2.0)
        cur_deg = cur_deg + span
        color = theme["accent"][idx % len(theme["accent"])]
        d_path = donut_slice_path(cx, cy, r_outer, r_inner, s_deg, e_deg)
        elements.append({
            "id": f"slice-{idx}",
            "type": "path",
            "act": 2,
            "anim": "reveal",
            "origin": f"{round(cx, 1)}px {round(cy, 1)}px",
            "d": d_path,
            "fill": color,
            "stroke": theme["bg"],
            "stroke_width": 2,
        })

    # Center hole readout
    hole_w = r_inner * 1.55 * m_ratio
    total_txt = text_mod.format_number(total)
    big_font = max(18, min(32, int(round(r_inner * 0.34 * f_scale))))
    tot_w = text_mod.measure_px(total_txt, big_font, True)
    if tot_w > r_inner * 1.75:
        fits = False
        overflow_path = "content.items"

    if center_label:
        cl_wrap = text_mod.wrap_lines(center_label, hole_w, label_font - 1, False, max_lines=2)
        if not cl_wrap["fits"]:
            fits = False
            overflow_path = "content.center_label"
        stack_h = big_font * 1.15 + 6.0 + cl_wrap["height"]
        top_cy = cy - stack_h / 2.0
        boxes.append(make_box("donut-center-val", "text", cx - tot_w / 2.0, top_cy, tot_w, big_font * 1.15, "donut-ring", "donut-ring", "content"))
        elements.append({
            "id": "donut-total",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": [total_txt],
            "x": cx,
            "y": top_cy,
            "font_size": big_font,
            "line_height": round(big_font * 1.15, 2),
            "fill": theme["ink"],
            "weight": 800,
            "anchor": "middle",
        })
        cl_y = top_cy + big_font * 1.15 + 4.0
        boxes.append(make_box("donut-center-lbl", "text", cx - cl_wrap["width"] / 2.0, cl_y, max(20.0, cl_wrap["width"]), cl_wrap["height"], "donut-ring", "donut-ring", "content.center_label"))
        elements.append({
            "id": "donut-center-label",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": cl_wrap["lines"],
            "x": cx,
            "y": cl_y,
            "font_size": label_font - 1,
            "line_height": cl_wrap["line_height"],
            "fill": theme["muted"],
            "weight": 600,
            "anchor": "middle",
        })
    else:
        top_cy = cy - big_font * 0.58
        elements.append({
            "id": "donut-total",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": [total_txt],
            "x": cx,
            "y": top_cy,
            "font_size": big_font,
            "line_height": round(big_font * 1.15, 2),
            "fill": theme["ink"],
            "weight": 800,
            "anchor": "middle",
        })

    # Legend cards
    for idx, it in enumerate(items):
        ipath = f"content.items[{idx}]"
        color = theme["accent"][idx % len(theme["accent"])]
        pct = (float(it["value"]) / total) * 100.0
        pct_str = f"{pct:.0f}%" if abs(pct - round(pct)) < 0.15 else f"{pct:.1f}%"
        val_str = f"{text_mod.format_number(float(it['value']))} ({pct_str})"

        if is_wide:
            rx = leg_x
            ry = leg_start_y + idx * (row_h + row_gap)
            rw = leg_w
            rh = row_h
        else:
            col_i = idx % 2
            row_i = idx // 2
            col_gap = 16.0 * g_scale
            rw = (leg_w - col_gap) / 2.0
            rx = leg_x + col_i * (rw + col_gap)
            ry = leg_start_y + row_i * (row_h + row_gap)
            rh = row_h

        if rh < label_font * 1.6:
            fits = False
            overflow_path = ipath

        cid = f"slice-card-{idx}"
        boxes.append(make_box(cid, "shape", rx, ry, rw, rh, cid, None, ipath))
        elements.append({
            "id": cid,
            "type": "rect",
            "act": 2,
            "anim": "reveal",
            "x": rx,
            "y": ry,
            "w": rw,
            "h": rh,
            "rx": 12,
            "fill": theme["surface"],
            "stroke": theme["border"],
            "stroke_width": 1,
        })
        elements.append({
            "id": f"slice-swatch-{idx}",
            "type": "rect",
            "act": 2,
            "anim": "reveal",
            "x": rx + 14.0,
            "y": ry + (rh - 22.0) / 2.0,
            "w": 10.0,
            "h": 22.0,
            "rx": 5,
            "fill": color,
        })

        vw = text_mod.measure_px(val_str, label_font, True)
        lbl_avail = (rw - 42.0 - vw - 16.0) * m_ratio
        l_wrap = text_mod.wrap_lines(it["label"], lbl_avail, body_font - 1, True, max_lines=2)
        if not l_wrap["fits"] or l_wrap["height"] > rh - 8.0:
            fits = False
            overflow_path = f"{ipath}.label"

        ly = ry + (rh - l_wrap["height"]) / 2.0
        boxes.append(make_box(f"slice-lbl-{idx}", "text", rx + 34.0, ly, max(16.0, l_wrap["width"]), l_wrap["height"], cid, cid, f"{ipath}.label"))
        elements.append({
            "id": f"slice-lbl-{idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": l_wrap["lines"],
            "x": rx + 34.0,
            "y": ly,
            "font_size": body_font - 1,
            "line_height": l_wrap["line_height"],
            "fill": theme["ink"],
            "weight": 650,
        })

        vy = ry + (rh - label_font * 1.25) / 2.0
        boxes.append(make_box(f"slice-val-{idx}", "text", rx + rw - 14.0 - vw, vy, vw, label_font * 1.25, cid, cid, f"{ipath}.value"))
        elements.append({
            "id": f"slice-val-{idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": [val_str],
            "x": rx + rw - 14.0,
            "y": vy,
            "font_size": label_font,
            "line_height": round(label_font * 1.25, 2),
            "fill": theme["muted"],
            "weight": 700,
            "anchor": "end",
        })

    return {
        "fits": fits,
        "overflow_path": overflow_path,
        "adjusted_path": overflow_path,
        "boxes": boxes,
        "elements": elements,
    }

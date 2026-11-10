"""Template: process — ordered step flow (3..6 steps) with connectors and flow dots."""

from typing import Any, Dict, List


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

    steps = spec["content"]["steps"]
    n = len(steps)
    is_wide = spec["aspect"] == "wide"

    head_font = scale_font("card_title", f_scale)
    body_font = scale_font("body", f_scale) - 1

    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    fits = True
    overflow_path = "content.steps"

    # Choose 1-row rail for 3..4 steps in wide; 2-row serpentine grid otherwise
    if is_wide and n <= 4:
        cols = n
        rows = 1
    elif n <= 4:
        cols = 2
        rows = 2
    else:
        cols = 3 if is_wide else 2
        rows = (n + cols - 1) // cols

    col_gap = (36.0 if rows == 1 else 32.0) * g_scale
    row_gap = 42.0 * g_scale
    card_w = (rect["w"] - col_gap * (cols - 1)) / float(cols)
    max_card_h = 260.0 if rows == 1 else 210.0
    card_h = min(max_card_h, (rect["h"] - row_gap * (rows - 1)) / float(rows))
    grid_h = rows * card_h + (rows - 1) * row_gap
    start_y = rect["y"] + (rect["h"] - grid_h) / 2.0

    if card_w < 150.0 or card_h < 105.0:
        return {"fits": False, "overflow_path": "content.steps", "boxes": boxes, "elements": elements}

    node_rects: List[Dict[str, float]] = []

    for idx, st in enumerate(steps):
        spath = f"content.steps[{idx}]"
        row_i = idx // cols
        col_in_row = idx % cols
        # Serpentine order on odd rows so step arrows never cross cards
        col_i = (cols - 1 - col_in_row) if (row_i % 2 == 1) else col_in_row

        nx = rect["x"] + col_i * (card_w + col_gap)
        ny = start_y + row_i * (card_h + row_gap)
        node_rects.append({"x": nx, "y": ny, "w": card_w, "h": card_h, "row": float(row_i), "col": float(col_i)})

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
            "rx": theme["radius"],
            "fill": theme["surface"],
            "stroke": theme["border"],
            "stroke_width": 1.5,
        })

        pad = 18.0
        badge_sz = 28.0
        by = ny + pad
        elements.append({
            "id": f"step-num-bg-{idx}",
            "type": "circle",
            "act": 2,
            "anim": "reveal",
            "cx": nx + pad + badge_sz / 2.0,
            "cy": by + badge_sz / 2.0,
            "r": badge_sz / 2.0,
            "fill": color,
        })
        elements.append({
            "id": f"step-num-{idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": [str(idx + 1)],
            "x": nx + pad + badge_sz / 2.0,
            "y": by + (badge_sz - 14.0) / 2.0,
            "font_size": 14,
            "line_height": 16,
            "fill": "#FFFFFF",
            "weight": 800,
            "anchor": "middle",
        })

        icon_name = st.get("icon")
        if icon_name:
            ix = nx + card_w - pad - 22.0
            iy = by + 3.0
            boxes.append(make_box(f"step-icon-{idx}", "icon", ix, iy, 22.0, 22.0, f"{nid}-icon", nid, f"{spath}.icon"))
            elements.append({
                "id": f"step-icon-{idx}",
                "type": "icon",
                "act": 2,
                "anim": "reveal",
                "icon": icon_name,
                "x": ix,
                "y": iy,
                "size": 22.0,
                "stroke": color,
            })

        cur_y = by + badge_sz + 12.0 * g_scale
        avail_w = (card_w - 2 * pad) * m_ratio
        t_wrap = text_mod.wrap_lines(st["title"], avail_w, head_font, True, max_lines=2)
        if not t_wrap["fits"]:
            fits = False
            overflow_path = f"{spath}.title"

        boxes.append(make_box(f"step-title-{idx}", "text", nx + pad, cur_y, max(20.0, t_wrap["width"]), t_wrap["height"], f"{nid}-title", nid, f"{spath}.title"))
        elements.append({
            "id": f"step-title-{idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": t_wrap["lines"],
            "x": nx + pad,
            "y": cur_y,
            "font_size": head_font,
            "line_height": t_wrap["line_height"],
            "fill": theme["ink"],
            "weight": 750,
        })
        cur_y = cur_y + t_wrap["height"] + 8.0 * g_scale

        detail = st.get("detail", "")
        if detail:
            d_wrap = text_mod.wrap_lines(detail, avail_w, body_font, False, max_lines=4)
            if not d_wrap["fits"] or (cur_y + d_wrap["height"] > ny + card_h - 12.0):
                fits = False
                overflow_path = f"{spath}.detail"
            boxes.append(make_box(f"step-detail-{idx}", "text", nx + pad, cur_y, max(20.0, d_wrap["width"]), d_wrap["height"], f"{nid}-detail", nid, f"{spath}.detail"))
            elements.append({
                "id": f"step-detail-{idx}",
                "type": "text",
                "act": 2,
                "anim": "reveal",
                "lines": d_wrap["lines"],
                "x": nx + pad,
                "y": cur_y,
                "font_size": body_font,
                "line_height": d_wrap["line_height"],
                "fill": theme["muted"],
                "weight": 450,
            })
        elif cur_y > ny + card_h - 10.0:
            fits = False
            overflow_path = f"{spath}.title"

    # Connectors (Act 3) and Flow Dots (Act 4)
    for idx in range(n - 1):
        a = node_rects[idx]
        b = node_rects[idx + 1]
        if int(a["row"]) == int(b["row"]):
            if a["x"] < b["x"]:
                x1 = a["x"] + a["w"] + 4.0
                x2 = b["x"] - 6.0
            else:
                x1 = a["x"] - 4.0
                x2 = b["x"] + b["w"] + 6.0
            ym = a["y"] + a["h"] / 2.0
            path_d = f"M {x1:.2f} {ym:.2f} L {x2:.2f} {ym:.2f}"
        else:
            xm = a["x"] + a["w"] / 2.0
            y1 = a["y"] + a["h"] + 4.0
            y2 = b["y"] - 6.0
            path_d = f"M {xm:.2f} {y1:.2f} L {xm:.2f} {y2:.2f}"

        elements.append({
            "id": f"edge-{idx}-{idx + 1}",
            "type": "path",
            "act": 3,
            "anim": "draw",
            "d": path_d,
            "stroke": theme["accent"][0],
            "stroke_width": 2.5,
            "marker_end": "arrow-accent",
        })
        elements.append({
            "id": f"flow-{idx}-{idx + 1}",
            "type": "flow_dot",
            "act": 4,
            "d": path_d,
            "r": 4.5,
            "fill": theme["accent"][0],
        })

    return {
        "fits": fits,
        "overflow_path": overflow_path,
        "adjusted_path": overflow_path,
        "boxes": boxes,
        "elements": elements,
    }

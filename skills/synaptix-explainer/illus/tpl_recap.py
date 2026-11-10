"""Template: recap — closing takeaways summary card (2..5 points)."""

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

    points = spec["content"]["points"]
    n = len(points)
    is_wide = spec["aspect"] == "wide"

    head_font = scale_font("card_title", f_scale)
    body_font = scale_font("body", f_scale) - 1

    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    fits = True
    overflow_path = "content.points"

    # Use 2 columns in wide when 4..5 points so cards stay spacious; stacked rows otherwise
    use_two_cols = is_wide and n >= 4
    cols = 2 if use_two_cols else 1
    rows = (n + cols - 1) // cols

    col_gap = 22.0 * g_scale
    row_gap = 16.0 * g_scale
    card_w = (rect["w"] - col_gap * (cols - 1)) / float(cols)
    card_h = min(140.0 if cols == 1 else 168.0, (rect["h"] - row_gap * (rows - 1)) / float(rows))
    grid_h = rows * card_h + (rows - 1) * row_gap
    start_y = rect["y"] + (rect["h"] - grid_h) / 2.0

    for idx, pt in enumerate(points):
        ppath = f"content.points[{idx}]"
        col_i = idx % cols
        row_i = idx // cols
        # Center a lone trailing card on the last row
        if cols == 2 and idx == n - 1 and (n % 2 == 1):
            px = rect["x"] + (rect["w"] - card_w) / 2.0
        else:
            px = rect["x"] + col_i * (card_w + col_gap)
        py = start_y + row_i * (card_h + row_gap)

        pid = f"recap-{idx}"
        color = theme["accent"][idx % len(theme["accent"])]

        boxes.append(make_box(pid, "shape", px, py, card_w, card_h, pid, None, ppath))
        elements.append({
            "id": pid,
            "type": "rect",
            "act": 2,
            "anim": "reveal",
            "x": px,
            "y": py,
            "w": card_w,
            "h": card_h,
            "rx": theme["radius"],
            "fill": theme["surface"],
            "stroke": theme["border"],
            "stroke_width": 1.5,
        })
        elements.append({
            "id": f"recap-strip-{idx}",
            "type": "rect",
            "act": 2,
            "anim": "reveal",
            "x": px,
            "y": py,
            "w": 6.0,
            "h": card_h,
            "rx": 3.0,
            "fill": color,
        })

        badge_r = 18.0
        bx = px + 26.0 + badge_r
        by = py + card_h / 2.0
        elements.append({
            "id": f"recap-num-bg-{idx}",
            "type": "circle",
            "act": 2,
            "anim": "reveal",
            "cx": bx,
            "cy": by,
            "r": badge_r,
            "fill": theme["surface_alt"],
            "stroke": color,
            "stroke_width": 2,
        })
        elements.append({
            "id": f"recap-num-{idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": [str(idx + 1)],
            "x": bx,
            "y": by - 8.0,
            "font_size": 15,
            "line_height": 18,
            "fill": color,
            "weight": 800,
            "anchor": "middle",
        })

        tx = px + 26.0 + badge_r * 2.0 + 20.0
        avail_w = (card_w - (tx - px) - 22.0) * m_ratio
        t_wrap = text_mod.wrap_lines(pt["title"], avail_w, head_font, True, max_lines=2)
        if not t_wrap["fits"]:
            fits = False
            overflow_path = f"{ppath}.title"

        detail = pt.get("detail", "")
        d_wrap = (
            text_mod.wrap_lines(detail, avail_w, body_font, False, max_lines=3)
            if detail
            else {"lines": [], "width": 0.0, "height": 0.0, "line_height": 20.0, "fits": True}
        )
        if not d_wrap["fits"]:
            fits = False
            overflow_path = f"{ppath}.detail"

        stack_h = t_wrap["height"] + (6.0 * g_scale + d_wrap["height"] if d_wrap["lines"] else 0.0)
        if stack_h > card_h - 18.0:
            fits = False
            overflow_path = f"{ppath}.detail" if detail else f"{ppath}.title"

        ty = py + (card_h - stack_h) / 2.0
        boxes.append(make_box(f"recap-title-{idx}", "text", tx, ty, max(20.0, t_wrap["width"]), t_wrap["height"], f"{pid}-t", pid, f"{ppath}.title"))
        elements.append({
            "id": f"recap-title-{idx}",
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

        if d_wrap["lines"]:
            dy = ty + t_wrap["height"] + 6.0 * g_scale
            boxes.append(make_box(f"recap-detail-{idx}", "text", tx, dy, max(20.0, d_wrap["width"]), d_wrap["height"], f"{pid}-d", pid, f"{ppath}.detail"))
            elements.append({
                "id": f"recap-detail-{idx}",
                "type": "text",
                "act": 2,
                "anim": "reveal",
                "lines": d_wrap["lines"],
                "x": tx,
                "y": dy,
                "font_size": body_font,
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

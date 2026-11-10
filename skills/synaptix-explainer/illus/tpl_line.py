"""Template: line-chart — multi-series trend over categories/time (1..3 series, 3..12 points)."""

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
    m_ratio = params["measure_ratio"]
    scale_font = params["scale_font"]
    make_box = params["make_box"]

    content = spec["content"]
    series_list = content["series"]
    y_label = content.get("y_label", "")
    label_font = scale_font("label", f_scale)

    all_y: List[float] = []
    for ser in series_list:
        for pt in ser["points"]:
            all_y.append(float(pt["y"]))

    min_y = min(all_y) if all_y else 0.0
    max_y = max(all_y) if all_y else 10.0
    if min_y > 0.0 and min_y < max_y * 0.35:
        min_y = 0.0
    ticks = text_mod.nice_ticks(min_y, max_y, 5)
    t_lo = ticks[0]
    t_hi = ticks[-1] if ticks[-1] > ticks[0] else ticks[0] + 1.0

    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    fits = True
    overflow_path = "content.series"

    # Top bar: y_label on left, series legend pills on right
    top_band_h = 0.0
    if y_label or len(series_list) >= 1:
        top_band_h = label_font + 20.0
        if y_label:
            yl_w = text_mod.wrap_lines(y_label, rect["w"] * 0.42, label_font, True, max_lines=1)
            if not yl_w["fits"]:
                fits = False
                overflow_path = "content.y_label"
            boxes.append(make_box("line-ylabel", "text", rect["x"], rect["y"], max(30.0, yl_w["width"]), yl_w["height"], "line-ylabel", None, "content.y_label"))
            elements.append({
                "id": "line-ylabel",
                "type": "text",
                "act": 1,
                "anim": "reveal",
                "lines": yl_w["lines"],
                "x": rect["x"],
                "y": rect["y"],
                "font_size": label_font,
                "line_height": yl_w["line_height"],
                "fill": theme["muted"],
                "weight": 600,
            })

        # Legend items aligned right-to-left
        cur_rx = rect["x"] + rect["w"]
        for s_idx in range(len(series_list) - 1, -1, -1):
            ser = series_list[s_idx]
            color = theme["accent"][s_idx % len(theme["accent"])]
            sw = text_mod.measure_px(ser["name"], label_font, True)
            item_w = sw + 24.0
            lx = cur_rx - item_w
            ly = rect["y"]
            boxes.append(make_box(f"legend-{s_idx}", "text", lx, ly, item_w, label_font + 6.0, f"legend-{s_idx}", None, f"content.series[{s_idx}].name"))
            elements.append({
                "id": f"legend-dot-{s_idx}",
                "type": "circle",
                "act": 1,
                "anim": "reveal",
                "cx": lx + 7.0,
                "cy": ly + label_font * 0.55,
                "r": 5.5,
                "fill": color,
            })
            elements.append({
                "id": f"legend-txt-{s_idx}",
                "type": "text",
                "act": 1,
                "anim": "reveal",
                "lines": [ser["name"]],
                "x": lx + 20.0,
                "y": ly,
                "font_size": label_font,
                "line_height": round(label_font * 1.25, 2),
                "fill": theme["ink"],
                "weight": 650,
            })
            cur_rx = lx - 22.0

    tick_w = 44.0
    for tv in ticks:
        tw = text_mod.measure_px(text_mod.format_number(tv), label_font - 1, False)
        if tw + 14.0 > tick_w:
            tick_w = tw + 14.0

    x_band = label_font * 2.4 + 14.0
    plot_x = rect["x"] + tick_w + 16.0
    plot_y = rect["y"] + top_band_h + 14.0
    plot_w = rect["w"] - tick_w - 36.0
    plot_h = rect["h"] - top_band_h - x_band - 14.0

    if plot_h < 120.0 or plot_w < 200.0:
        return {"fits": False, "overflow_path": "content.series", "boxes": boxes, "elements": elements}

    # Grid & Y ticks (Act 1)
    for idx_t, tv in enumerate(ticks):
        ratio = (tv - t_lo) / (t_hi - t_lo)
        gy = plot_y + plot_h * (1.0 - ratio)
        elements.append({
            "id": f"lgrid-{idx_t}",
            "type": "line",
            "act": 1,
            "anim": "reveal",
            "x1": plot_x,
            "y1": gy,
            "x2": plot_x + plot_w,
            "y2": gy,
            "stroke": theme["border"] if abs(tv - t_lo) < 1e-9 else theme["grid"],
            "stroke_width": 1.5 if abs(tv - t_lo) < 1e-9 else 1,
            "dash": "" if abs(tv - t_lo) < 1e-9 else "4 4",
        })
        t_str = text_mod.format_number(tv)
        tw = text_mod.measure_px(t_str, label_font - 1, False)
        ty = gy - (label_font - 1) * 0.55
        boxes.append(make_box(f"lytick-{idx_t}", "text", plot_x - 12.0 - tw, ty, tw, label_font + 2.0, f"lytick-{idx_t}", None, "content"))
        elements.append({
            "id": f"lytick-{idx_t}",
            "type": "text",
            "act": 1,
            "anim": "reveal",
            "lines": [t_str],
            "x": plot_x - 12.0,
            "y": ty,
            "font_size": label_font - 1,
            "line_height": label_font + 2.0,
            "fill": theme["muted"],
            "weight": 500,
            "anchor": "end",
        })

    first_pts = series_list[0]["points"]
    num_pts = len(first_pts)
    step_x = plot_w / float(max(1, num_pts - 1))

    # X-axis labels
    slot_x_w = max(28.0, (plot_w / float(num_pts)) * 0.92 * m_ratio)
    for p_idx, pt in enumerate(first_pts):
        px = plot_x + p_idx * step_x
        xw = text_mod.wrap_lines(pt["x"], slot_x_w, label_font - 1, False, max_lines=2)
        if not xw["fits"]:
            fits = False
            overflow_path = f"content.series[0].points[{p_idx}].x"
        ly = plot_y + plot_h + 12.0
        bw = max(14.0, xw["width"])
        # Clamp edge labels inside frame cleanly
        anchor = "middle"
        tx = px
        bx = px - bw / 2.0
        if p_idx == num_pts - 1 and (px + bw / 2.0) > (rect["x"] + rect["w"]):
            anchor = "end"
            tx = rect["x"] + rect["w"]
            bx = tx - bw
        boxes.append(make_box(f"xlbl-{p_idx}", "text", bx, ly, bw, xw["height"], f"xlbl-{p_idx}", None, f"content.series[0].points[{p_idx}].x"))
        elements.append({
            "id": f"xlbl-{p_idx}",
            "type": "text",
            "act": 1,
            "anim": "reveal",
            "lines": xw["lines"],
            "x": tx,
            "y": ly,
            "font_size": label_font - 1,
            "line_height": xw["line_height"],
            "fill": theme["ink"],
            "weight": 600,
            "anchor": anchor,
        })

    # Series paths (Act 3 draw) + markers (Act 2 reveal)
    for s_idx, ser in enumerate(series_list):
        color = theme["accent"][s_idx % len(theme["accent"])]
        pts = ser["points"]
        d_parts: List[str] = []
        coords: List[ Any ] = []
        for p_idx, pt in enumerate(pts):
            px = plot_x + p_idx * step_x
            ratio = (float(pt["y"]) - t_lo) / (t_hi - t_lo)
            py = plot_y + plot_h * (1.0 - ratio)
            coords.append((px, py, pt["y"]))
            cmd = "M" if p_idx == 0 else "L"
            d_parts.append(f"{cmd} {round(px, 2)} {round(py, 2)}")

        elements.append({
            "id": f"series-line-{s_idx}",
            "type": "path",
            "act": 3,
            "anim": "draw",
            "d": " ".join(d_parts),
            "stroke": color,
            "stroke_width": 3.5,
        })

        for p_idx, (px, py, _) in enumerate(coords):
            elements.append({
                "id": f"pt-{s_idx}-{p_idx}",
                "type": "circle",
                "act": 2,
                "anim": "reveal",
                "cx": px,
                "cy": py,
                "r": 5.5,
                "fill": theme["surface"],
                "stroke": color,
                "stroke_width": 3,
            })

    return {
        "fits": fits,
        "overflow_path": overflow_path,
        "adjusted_path": overflow_path,
        "boxes": boxes,
        "elements": elements,
    }

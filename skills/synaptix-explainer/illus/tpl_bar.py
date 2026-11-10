"""Template: bar-chart — vertical bar comparison (2..8 bars)."""

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

    content = spec["content"]
    items = content["items"]
    y_label = content.get("y_label", "")
    n = len(items)

    label_font = scale_font("label", f_scale)
    val_font = scale_font("label", f_scale)

    max_v = 0.0
    for it in items:
        if it["value"] > max_v:
            max_v = it["value"]
    ticks = text_mod.nice_ticks(0.0, max_v if max_v > 0 else 10.0, 5)
    y_max = max(ticks[-1], 1e-6)

    # Measure tick label column width
    tick_w = 40.0
    for tv in ticks:
        tw = text_mod.measure_px(text_mod.format_number(tv), label_font, False)
        if tw + 14.0 > tick_w:
            tick_w = tw + 14.0

    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    fits = True
    overflow_path = "content.items"

    # Optional y_label above axis
    top_offset = 0.0
    if y_label:
        yl_wrap = text_mod.wrap_lines(y_label, rect["w"] * 0.6, label_font, True, max_lines=1)
        if not yl_wrap["fits"]:
            fits = False
            overflow_path = "content.y_label"
        boxes.append(make_box("bar-ylabel", "text", rect["x"], rect["y"], max(30.0, yl_wrap["width"]), yl_wrap["height"], "y-label", None, "content.y_label"))
        elements.append({
            "id": "bar-ylabel",
            "type": "text",
            "act": 1,
            "anim": "reveal",
            "lines": yl_wrap["lines"],
            "x": rect["x"],
            "y": rect["y"],
            "font_size": label_font,
            "line_height": yl_wrap["line_height"],
            "fill": theme["muted"],
            "weight": 600,
        })
        top_offset = yl_wrap["height"] + 16.0

    x_label_band = label_font * 2.9 + 14.0
    val_headroom = val_font * 1.5 + 12.0
    plot_x = rect["x"] + tick_w + 12.0
    plot_y = rect["y"] + top_offset + val_headroom
    plot_w = rect["w"] - tick_w - 20.0
    plot_h = rect["h"] - top_offset - val_headroom - x_label_band

    if plot_h < 120.0 or plot_w < 200.0:
        return {"fits": False, "overflow_path": "content.items", "boxes": boxes, "elements": elements}

    # Gridlines & Y ticks (Act 1)
    for t_idx, tv in enumerate(ticks):
        ratio = tv / y_max
        gy = plot_y + plot_h * (1.0 - ratio)
        elements.append({
            "id": f"grid-{t_idx}",
            "type": "line",
            "act": 1,
            "anim": "reveal",
            "x1": plot_x,
            "y1": gy,
            "x2": plot_x + plot_w,
            "y2": gy,
            "stroke": theme["border"] if t_idx == 0 else theme["grid"],
            "stroke_width": 1.5 if t_idx == 0 else 1,
            "dash": "" if t_idx == 0 else "4 4",
        })
        t_str = text_mod.format_number(tv)
        tw = text_mod.measure_px(t_str, label_font - 1, False)
        ty = gy - (label_font - 1) * 0.55
        boxes.append(make_box(f"ytick-{t_idx}", "text", plot_x - 12.0 - tw, ty, tw, label_font + 2.0, f"ytick-{t_idx}", None, "content"))
        elements.append({
            "id": f"ytick-{t_idx}",
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

    slot_w = plot_w / float(n)
    gap = max(12.0, slot_w * 0.26 * g_scale)
    bar_w = min(112.0, max(24.0, slot_w - gap))
    accents = theme["accent"]

    for idx, it in enumerate(items):
        ipath = f"content.items[{idx}]"
        cx = plot_x + slot_w * (idx + 0.5)
        bx = cx - bar_w / 2.0
        val = float(it["value"])
        bh = max(4.0, (val / y_max) * plot_h) if val > 0 else 2.0
        by = plot_y + plot_h - bh
        color = accents[idx % len(accents)]

        # Bar shape (Act 2: scaleY from baseline)
        boxes.append(make_box(f"bar-{idx}", "shape", bx, by, bar_w, bh, f"bar-col-{idx}", None, ipath))
        elements.append({
            "id": f"bar-{idx}",
            "type": "rect",
            "act": 2,
            "anim": "bar-grow",
            "origin": f"{round(cx, 1)}px {round(plot_y + plot_h, 1)}px",
            "x": bx,
            "y": by,
            "w": bar_w,
            "h": bh,
            "rx": min(8.0, bar_w * 0.16),
            "fill": color,
        })

        # Value label above bar
        v_txt = text_mod.format_number(val, it.get("unit", ""))
        vw = text_mod.measure_px(v_txt, val_font, True)
        if vw > slot_w - 4.0:
            fits = False
            overflow_path = f"{ipath}.value"
        vy = by - val_font * 1.25 - 5.0
        boxes.append(make_box(f"bar-val-{idx}", "text", cx - vw / 2.0, vy, vw, val_font * 1.25, f"bar-col-{idx}", None, f"{ipath}.value"))
        elements.append({
            "id": f"bar-val-{idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": [v_txt],
            "x": cx,
            "y": vy,
            "font_size": val_font,
            "line_height": round(val_font * 1.25, 2),
            "fill": theme["ink"],
            "weight": 700,
            "anchor": "middle",
        })

        # X-axis category label below baseline
        lbl_max_w = (slot_w - 8.0) * m_ratio
        l_wrap = text_mod.wrap_lines(it["label"], lbl_max_w, label_font, False, max_lines=2)
        if not l_wrap["fits"]:
            fits = False
            overflow_path = f"{ipath}.label"
        ly = plot_y + plot_h + 10.0
        lw = max(16.0, l_wrap["width"])
        boxes.append(make_box(f"bar-lbl-{idx}", "text", cx - lw / 2.0, ly, lw, l_wrap["height"], f"bar-lbl-{idx}", None, f"{ipath}.label"))
        elements.append({
            "id": f"bar-lbl-{idx}",
            "type": "text",
            "act": 1,
            "anim": "reveal",
            "lines": l_wrap["lines"],
            "x": cx,
            "y": ly,
            "font_size": label_font,
            "line_height": l_wrap["line_height"],
            "fill": theme["ink"],
            "weight": 600,
            "anchor": "middle",
        })

    return {
        "fits": fits,
        "overflow_path": overflow_path,
        "adjusted_path": overflow_path,
        "boxes": boxes,
        "elements": elements,
    }

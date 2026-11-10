"""Template: hub — central core concept with 3..6 radial spokes and flow dots."""

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
    center = content["center"]
    spokes = content["spokes"]
    n = len(spokes)
    is_wide = spec["aspect"] == "wide"

    head_font = scale_font("card_title", f_scale) - 1
    body_font = scale_font("label", f_scale)

    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    fits = True
    overflow_path = "content.spokes"

    # Symmetric 3-column layout: Left Spokes | Center Hub | Right Spokes
    chan_gap = (78.0 if is_wide else 48.0) * (0.85 + 0.15 * g_scale)
    hub_w = (290.0 if is_wide else 256.0) * (0.92 + 0.08 * g_scale)
    spoke_w = (rect["w"] - hub_w - 2.0 * chan_gap) / 2.0

    cx = rect["x"] + rect["w"] / 2.0
    cy = rect["y"] + rect["h"] / 2.0
    hub_x = cx - hub_w / 2.0

    # Build Center Hub Card (Act 2)
    hub_pad = 20.0
    hub_avail = (hub_w - 2 * hub_pad) * m_ratio
    ct_wrap = text_mod.wrap_lines(center["title"], hub_avail, head_font + 2, True, max_lines=2)
    if not ct_wrap["fits"]:
        fits = False
        overflow_path = "content.center.title"

    cd_txt = center.get("detail", "")
    cd_wrap = (
        text_mod.wrap_lines(cd_txt, hub_avail, body_font, False, max_lines=4)
        if cd_txt
        else {"lines": [], "width": 0.0, "height": 0.0, "line_height": 18.0, "fits": True}
    )
    if not cd_wrap["fits"]:
        fits = False
        overflow_path = "content.center.detail"

    hub_inner_h = ct_wrap["height"] + (10.0 + cd_wrap["height"] if cd_wrap["lines"] else 0.0)
    hub_h = min(rect["h"] * 0.62, max(124.0, hub_inner_h + 44.0))
    if hub_inner_h > hub_h - 24.0:
        fits = False
        overflow_path = "content.center.detail" if cd_txt else "content.center.title"

    hub_y = cy - hub_h / 2.0
    boxes.append(make_box("hub-center", "shape", hub_x, hub_y, hub_w, hub_h, "hub-center", None, "content.center"))
    elements.append({
        "id": "hub-center",
        "type": "rect",
        "act": 2,
        "anim": "reveal",
        "x": hub_x,
        "y": hub_y,
        "w": hub_w,
        "h": hub_h,
        "rx": theme["radius"] * 1.15,
        "fill": theme["surface_alt"],
        "stroke": theme["accent"][0],
        "stroke_width": 2.5,
    })

    hty = cy - hub_inner_h / 2.0
    boxes.append(make_box("hub-title", "text", cx - ct_wrap["width"] / 2.0, hty, max(20.0, ct_wrap["width"]), ct_wrap["height"], "hub-center-t", "hub-center", "content.center.title"))
    elements.append({
        "id": "hub-title",
        "type": "text",
        "act": 2,
        "anim": "reveal",
        "lines": ct_wrap["lines"],
        "x": cx,
        "y": hty,
        "font_size": head_font + 2,
        "line_height": ct_wrap["line_height"],
        "fill": theme["ink"],
        "weight": 800,
        "anchor": "middle",
    })
    if cd_wrap["lines"]:
        hdy = hty + ct_wrap["height"] + 10.0
        boxes.append(make_box("hub-detail", "text", cx - cd_wrap["width"] / 2.0, hdy, max(20.0, cd_wrap["width"]), cd_wrap["height"], "hub-center-d", "hub-center", "content.center.detail"))
        elements.append({
            "id": "hub-detail",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": cd_wrap["lines"],
            "x": cx,
            "y": hdy,
            "font_size": body_font,
            "line_height": cd_wrap["line_height"],
            "fill": theme["muted"],
            "weight": 450,
            "anchor": "middle",
        })

    # Split spokes across left and right columns
    left_count = (n + 1) // 2
    right_count = n - left_count
    max_per_side = max(left_count, right_count)
    v_gap = 18.0 * g_scale
    spoke_h = min(158.0 if is_wide else 196.0, (rect["h"] - v_gap * max(0, max_per_side - 1)) / float(max(1, max_per_side)))

    for idx, sp in enumerate(spokes):
        spath = f"content.spokes[{idx}]"
        is_left = idx < left_count
        side_idx = idx if is_left else (idx - left_count)
        side_total = left_count if is_left else right_count

        col_stack_h = side_total * spoke_h + max(0, side_total - 1) * v_gap
        col_top_y = rect["y"] + (rect["h"] - col_stack_h) / 2.0

        sx = rect["x"] if is_left else (hub_x + hub_w + chan_gap)
        sy = col_top_y + side_idx * (spoke_h + v_gap)
        sid = f"spoke-{idx}"
        color = theme["accent"][(idx + 1) % len(theme["accent"])]

        # Curved spoke connector from Hub -> Spoke (Act 3 draw + Act 4 flow dot)
        start_x = hub_x if is_left else (hub_x + hub_w)
        end_x = (sx + spoke_w) if is_left else sx
        start_y = hub_y + hub_h * ((side_idx + 1.0) / float(side_total + 1.0))
        end_y = sy + spoke_h / 2.0
        ctrl_dx = (end_x - start_x) * 0.52
        spoke_d = (
            f"M {start_x:.2f} {start_y:.2f} "
            f"C {start_x + ctrl_dx:.2f} {start_y:.2f}, "
            f"{end_x - ctrl_dx:.2f} {end_y:.2f}, "
            f"{end_x:.2f} {end_y:.2f}"
        )
        elements.append({
            "id": f"edge-hub-{idx}",
            "type": "path",
            "act": 3,
            "anim": "draw",
            "d": spoke_d,
            "stroke": color,
            "stroke_width": 2.2,
        })
        elements.append({
            "id": f"flow-hub-{idx}",
            "type": "flow_dot",
            "act": 4,
            "d": spoke_d,
            "r": 4.2,
            "fill": color,
        })

        # Spoke card
        boxes.append(make_box(sid, "shape", sx, sy, spoke_w, spoke_h, sid, None, spath))
        elements.append({
            "id": sid,
            "type": "rect",
            "act": 2,
            "anim": "reveal",
            "x": sx,
            "y": sy,
            "w": spoke_w,
            "h": spoke_h,
            "rx": 14,
            "fill": theme["surface"],
            "stroke": theme["border"],
            "stroke_width": 1.5,
        })

        pad = 16.0
        icon_name = sp.get("icon")
        title_x = sx + pad
        title_avail = (spoke_w - 2 * pad) * m_ratio

        if icon_name:
            boxes.append(make_box(f"spoke-icon-{idx}", "icon", sx + pad, sy + pad, 20.0, 20.0, f"{sid}-icon", sid, f"{spath}.icon"))
            elements.append({
                "id": f"spoke-icon-{idx}",
                "type": "icon",
                "act": 2,
                "anim": "reveal",
                "icon": icon_name,
                "x": sx + pad,
                "y": sy + pad,
                "size": 20.0,
                "stroke": color,
            })
            title_x = sx + pad + 28.0
            title_avail = (spoke_w - 2 * pad - 28.0) * m_ratio

        st_wrap = text_mod.wrap_lines(sp["title"], title_avail, head_font, True, max_lines=2)
        if not st_wrap["fits"]:
            fits = False
            overflow_path = f"{spath}.title"

        boxes.append(make_box(f"spoke-title-{idx}", "text", title_x, sy + pad, max(18.0, st_wrap["width"]), st_wrap["height"], f"{sid}-t", sid, f"{spath}.title"))
        elements.append({
            "id": f"spoke-title-{idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": st_wrap["lines"],
            "x": title_x,
            "y": sy + pad,
            "font_size": head_font,
            "line_height": st_wrap["line_height"],
            "fill": theme["ink"],
            "weight": 750,
        })

        cur_y = sy + pad + max(22.0, st_wrap["height"]) + 6.0 * g_scale
        sdetail = sp.get("detail", "")
        if sdetail:
            sd_avail = (spoke_w - 2 * pad) * m_ratio
            sd_wrap = text_mod.wrap_lines(sdetail, sd_avail, body_font - 1, False, max_lines=4)
            if not sd_wrap["fits"] or (cur_y + sd_wrap["height"] > sy + spoke_h - 10.0):
                fits = False
                overflow_path = f"{spath}.detail"
            boxes.append(make_box(f"spoke-detail-{idx}", "text", sx + pad, cur_y, max(18.0, sd_wrap["width"]), sd_wrap["height"], f"{sid}-d", sid, f"{spath}.detail"))
            elements.append({
                "id": f"spoke-detail-{idx}",
                "type": "text",
                "act": 2,
                "anim": "reveal",
                "lines": sd_wrap["lines"],
                "x": sx + pad,
                "y": cur_y,
                "font_size": body_font - 1,
                "line_height": sd_wrap["line_height"],
                "fill": theme["muted"],
                "weight": 450,
            })
        elif cur_y > sy + spoke_h - 8.0:
            fits = False
            overflow_path = f"{spath}.title"

    return {
        "fits": fits,
        "overflow_path": overflow_path,
        "adjusted_path": overflow_path,
        "boxes": boxes,
        "elements": elements,
    }

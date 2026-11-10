"""Template: timeline — chronological milestone spine (3..7 events)."""

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

    events = spec["content"]["events"]
    n = len(events)
    is_wide = spec["aspect"] == "wide"

    head_font = scale_font("card_title", f_scale) - 1
    body_font = scale_font("label", f_scale)

    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    fits = True
    overflow_path = "content.events"

    if is_wide:
        # Horizontal spine across center, alternating cards above & below so adjacent cards never collide
        spine_y = rect["y"] + rect["h"] * 0.5
        spine_x1 = rect["x"] + 20.0
        spine_x2 = rect["x"] + rect["w"] - 20.0
        elements.append({
            "id": "timeline-spine",
            "type": "line",
            "act": 3,
            "anim": "draw",
            "x1": spine_x1,
            "y1": spine_y,
            "x2": spine_x2,
            "y2": spine_y,
            "stroke": theme["border"],
            "stroke_width": 3,
        })

        # Top lane has ceil(n/2) cards, bottom lane has floor(n/2) cards
        top_count = (n + 1) // 2
        lane_slots = max(2, top_count)
        max_card_w = min(310.0, (rect["w"] - 24.0 * g_scale * (lane_slots - 1)) / float(lane_slots))
        stem_len = 28.0 * g_scale
        card_h = min(176.0, rect["h"] * 0.5 - stem_len - 10.0)

        step_x = (rect["w"] - max_card_w) / float(max(1, n - 1))

        for idx, ev in enumerate(events):
            epath = f"content.events[{idx}]"
            is_top = (idx % 2) == 0
            ecx = rect["x"] + max_card_w / 2.0 + idx * step_x
            cx_card = ecx - max_card_w / 2.0
            cy_card = (spine_y - stem_len - card_h) if is_top else (spine_y + stem_len)
            color = theme["accent"][idx % len(theme["accent"])]
            cid = f"event-{idx}"

            # Stem + milestone dot
            stem_y2 = (cy_card + card_h) if is_top else cy_card
            elements.append({
                "id": f"stem-{idx}",
                "type": "line",
                "act": 3,
                "anim": "draw",
                "x1": ecx,
                "y1": spine_y,
                "x2": ecx,
                "y2": stem_y2,
                "stroke": color,
                "stroke_width": 2,
            })
            elements.append({
                "id": f"dot-{idx}",
                "type": "circle",
                "act": 2,
                "anim": "reveal",
                "cx": ecx,
                "cy": spine_y,
                "r": 7.0,
                "fill": color,
                "stroke": theme["bg"],
                "stroke_width": 2.5,
            })

            boxes.append(make_box(cid, "shape", cx_card, cy_card, max_card_w, card_h, cid, None, epath))
            elements.append({
                "id": cid,
                "type": "rect",
                "act": 2,
                "anim": "reveal",
                "x": cx_card,
                "y": cy_card,
                "w": max_card_w,
                "h": card_h,
                "rx": 14,
                "fill": theme["surface"],
                "stroke": theme["border"],
                "stroke_width": 1.5,
            })

            pad = 14.0
            avail_w = (max_card_w - 2 * pad) * m_ratio
            cur_y = cy_card + pad

            when_w = min(avail_w, text_mod.measure_px(ev["when"], 12, True) + 20.0)
            elements.append({
                "id": f"when-bg-{idx}",
                "type": "rect",
                "act": 2,
                "anim": "reveal",
                "x": cx_card + pad,
                "y": cur_y,
                "w": when_w,
                "h": 22.0,
                "rx": 11.0,
                "fill": theme["surface_alt"],
            })
            elements.append({
                "id": f"when-txt-{idx}",
                "type": "text",
                "act": 2,
                "anim": "reveal",
                "lines": [ev["when"]],
                "x": cx_card + pad + when_w / 2.0,
                "y": cur_y + 4.0,
                "font_size": 12,
                "line_height": 14,
                "fill": color,
                "weight": 750,
                "anchor": "middle",
            })
            cur_y = cur_y + 28.0 * g_scale

            t_wrap = text_mod.wrap_lines(ev["title"], avail_w, head_font, True, max_lines=2)
            if not t_wrap["fits"]:
                fits = False
                overflow_path = f"{epath}.title"
            boxes.append(make_box(f"ev-title-{idx}", "text", cx_card + pad, cur_y, max(20.0, t_wrap["width"]), t_wrap["height"], f"{cid}-t", cid, f"{epath}.title"))
            elements.append({
                "id": f"ev-title-{idx}",
                "type": "text",
                "act": 2,
                "anim": "reveal",
                "lines": t_wrap["lines"],
                "x": cx_card + pad,
                "y": cur_y,
                "font_size": head_font,
                "line_height": t_wrap["line_height"],
                "fill": theme["ink"],
                "weight": 750,
            })
            cur_y = cur_y + t_wrap["height"] + 6.0 * g_scale

            detail = ev.get("detail", "")
            if detail:
                d_wrap = text_mod.wrap_lines(detail, avail_w, body_font - 1, False, max_lines=3)
                if not d_wrap["fits"] or (cur_y + d_wrap["height"] > cy_card + card_h - 10.0):
                    fits = False
                    overflow_path = f"{epath}.detail"
                boxes.append(make_box(f"ev-detail-{idx}", "text", cx_card + pad, cur_y, max(20.0, d_wrap["width"]), d_wrap["height"], f"{cid}-d", cid, f"{epath}.detail"))
                elements.append({
                    "id": f"ev-detail-{idx}",
                    "type": "text",
                    "act": 2,
                    "anim": "reveal",
                    "lines": d_wrap["lines"],
                    "x": cx_card + pad,
                    "y": cur_y,
                    "font_size": body_font - 1,
                    "line_height": d_wrap["line_height"],
                    "fill": theme["muted"],
                    "weight": 450,
                })
            elif cur_y > cy_card + card_h - 8.0:
                fits = False
                overflow_path = f"{epath}.title"
    else:
        # Square aspect: clean vertical spine on left with full-width milestone cards
        spine_x = rect["x"] + 118.0
        row_gap = 12.0 * g_scale
        row_h = min(112.0, (rect["h"] - row_gap * (n - 1)) / float(n))
        total_h = n * row_h + (n - 1) * row_gap
        start_y = rect["y"] + (rect["h"] - total_h) / 2.0

        elements.append({
            "id": "timeline-spine",
            "type": "line",
            "act": 3,
            "anim": "draw",
            "x1": spine_x,
            "y1": start_y + row_h * 0.5,
            "x2": spine_x,
            "y2": start_y + total_h - row_h * 0.5,
            "stroke": theme["border"],
            "stroke_width": 3,
        })

        for idx, ev in enumerate(events):
            epath = f"content.events[{idx}]"
            ry = start_y + idx * (row_h + row_gap)
            ymid = ry + row_h * 0.5
            color = theme["accent"][idx % len(theme["accent"])]
            cid = f"event-{idx}"

            # Left 'when' label
            ww = text_mod.measure_px(ev["when"], body_font, True)
            boxes.append(make_box(f"when-{idx}", "text", spine_x - 20.0 - ww, ymid - body_font * 0.6, ww, body_font * 1.25, f"{cid}-when", None, f"{epath}.when"))
            elements.append({
                "id": f"when-{idx}",
                "type": "text",
                "act": 2,
                "anim": "reveal",
                "lines": [ev["when"]],
                "x": spine_x - 20.0,
                "y": ymid - body_font * 0.6,
                "font_size": body_font,
                "line_height": round(body_font * 1.25, 2),
                "fill": color,
                "weight": 750,
                "anchor": "end",
            })

            elements.append({
                "id": f"dot-{idx}",
                "type": "circle",
                "act": 2,
                "anim": "reveal",
                "cx": spine_x,
                "cy": ymid,
                "r": 7.0,
                "fill": color,
                "stroke": theme["bg"],
                "stroke_width": 2.5,
            })

            cx_card = spine_x + 26.0
            cw_card = rect["x"] + rect["w"] - cx_card
            boxes.append(make_box(cid, "shape", cx_card, ry, cw_card, row_h, cid, None, epath))
            elements.append({
                "id": cid,
                "type": "rect",
                "act": 2,
                "anim": "reveal",
                "x": cx_card,
                "y": ry,
                "w": cw_card,
                "h": row_h,
                "rx": 12,
                "fill": theme["surface"],
                "stroke": theme["border"],
                "stroke_width": 1.5,
            })

            pad_x = 18.0
            avail_w = (cw_card - 2 * pad_x) * m_ratio
            t_wrap = text_mod.wrap_lines(ev["title"], avail_w, head_font, True, max_lines=1)
            if not t_wrap["fits"]:
                fits = False
                overflow_path = f"{epath}.title"

            detail = ev.get("detail", "")
            d_wrap = (
                text_mod.wrap_lines(detail, avail_w, body_font - 1, False, max_lines=2)
                if detail
                else {"lines": [], "width": 0.0, "height": 0.0, "line_height": 18.0, "fits": True}
            )
            if not d_wrap["fits"]:
                fits = False
                overflow_path = f"{epath}.detail"

            stack_h = t_wrap["height"] + (4.0 + d_wrap["height"] if d_wrap["lines"] else 0.0)
            if stack_h > row_h - 12.0:
                fits = False
                overflow_path = f"{epath}.detail" if detail else f"{epath}.title"

            ty = ry + (row_h - stack_h) / 2.0
            boxes.append(make_box(f"ev-title-{idx}", "text", cx_card + pad_x, ty, max(20.0, t_wrap["width"]), t_wrap["height"], f"{cid}-t", cid, f"{epath}.title"))
            elements.append({
                "id": f"ev-title-{idx}",
                "type": "text",
                "act": 2,
                "anim": "reveal",
                "lines": t_wrap["lines"],
                "x": cx_card + pad_x,
                "y": ty,
                "font_size": head_font,
                "line_height": t_wrap["line_height"],
                "fill": theme["ink"],
                "weight": 750,
            })
            if d_wrap["lines"]:
                dy = ty + t_wrap["height"] + 4.0
                boxes.append(make_box(f"ev-detail-{idx}", "text", cx_card + pad_x, dy, max(20.0, d_wrap["width"]), d_wrap["height"], f"{cid}-d", cid, f"{epath}.detail"))
                elements.append({
                    "id": f"ev-detail-{idx}",
                    "type": "text",
                    "act": 2,
                    "anim": "reveal",
                    "lines": d_wrap["lines"],
                    "x": cx_card + pad_x,
                    "y": dy,
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

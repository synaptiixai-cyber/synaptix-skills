"""Template: comparison — side-by-side option cards (2..3 columns) + optional verdict."""

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
    columns = content["columns"]
    verdict = content.get("verdict", "")
    ncols = len(columns)

    head_font = scale_font("card_title", f_scale)
    body_font = scale_font("body", f_scale)

    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    fits = True
    overflow_path = "content.columns"

    verdict_h = 0.0
    verdict_gap = 18.0 * g_scale
    v_wrap: Dict[str, Any] = {"lines": [], "width": 0.0, "height": 0.0, "line_height": 22.0, "fits": True}
    if verdict:
        v_wrap = text_mod.wrap_lines(verdict, (rect["w"] - 48.0) * m_ratio, body_font, True, max_lines=2)
        if not v_wrap["fits"]:
            fits = False
            overflow_path = "content.verdict"
        verdict_h = max(48.0, v_wrap["height"] + 24.0)

    cols_h = rect["h"] - (verdict_h + verdict_gap if verdict else 0.0)
    col_gap = 22.0 * g_scale
    col_w = (rect["w"] - col_gap * (ncols - 1)) / float(ncols)

    if cols_h < 150.0 or col_w < 180.0:
        return {"fits": False, "overflow_path": "content.columns", "boxes": boxes, "elements": elements}

    for c_idx, col in enumerate(columns):
        cpath = f"content.columns[{c_idx}]"
        cx = rect["x"] + c_idx * (col_w + col_gap)
        cy = rect["y"]
        color = theme["accent"][c_idx % len(theme["accent"])]
        cid = f"col-{c_idx}"

        boxes.append(make_box(cid, "shape", cx, cy, col_w, cols_h, cid, None, cpath))
        elements.append({
            "id": cid,
            "type": "rect",
            "act": 2,
            "anim": "reveal",
            "x": cx,
            "y": cy,
            "w": col_w,
            "h": cols_h,
            "rx": theme["radius"],
            "fill": theme["surface"],
            "stroke": theme["border"],
            "stroke_width": 1.5,
        })
        elements.append({
            "id": f"col-accent-{c_idx}",
            "type": "rect",
            "act": 2,
            "anim": "reveal",
            "x": cx,
            "y": cy,
            "w": col_w,
            "h": 6.0,
            "rx": 3.0,
            "fill": color,
        })

        pad_x = 22.0
        cur_y = cy + 22.0
        icon_name = col.get("icon")
        title_x = cx + pad_x
        title_avail = (col_w - 2 * pad_x) * m_ratio

        if icon_name:
            icon_sz = 24.0
            boxes.append(make_box(f"col-icon-{c_idx}", "icon", cx + pad_x, cur_y, icon_sz, icon_sz, f"{cid}-hdr-icon", cid, f"{cpath}.icon"))
            elements.append({
                "id": f"col-icon-{c_idx}",
                "type": "icon",
                "act": 2,
                "anim": "reveal",
                "icon": icon_name,
                "x": cx + pad_x,
                "y": cur_y,
                "size": icon_sz,
                "stroke": color,
            })
            title_x = cx + pad_x + icon_sz + 12.0
            title_avail = (col_w - 2 * pad_x - icon_sz - 12.0) * m_ratio

        t_wrap = text_mod.wrap_lines(col["title"], title_avail, head_font, True, max_lines=2)
        if not t_wrap["fits"]:
            fits = False
            overflow_path = f"{cpath}.title"
        boxes.append(make_box(f"col-title-{c_idx}", "text", title_x, cur_y, max(20.0, t_wrap["width"]), t_wrap["height"], f"{cid}-hdr-txt", cid, f"{cpath}.title"))
        elements.append({
            "id": f"col-title-{c_idx}",
            "type": "text",
            "act": 2,
            "anim": "reveal",
            "lines": t_wrap["lines"],
            "x": title_x,
            "y": cur_y,
            "font_size": head_font,
            "line_height": t_wrap["line_height"],
            "fill": theme["ink"],
            "weight": 750,
        })

        cur_y = cur_y + max(26.0, t_wrap["height"]) + 14.0
        elements.append({
            "id": f"col-sep-{c_idx}",
            "type": "line",
            "act": 2,
            "anim": "reveal",
            "x1": cx + pad_x,
            "y1": cur_y,
            "x2": cx + col_w - pad_x,
            "y2": cur_y,
            "stroke": theme["grid"],
            "stroke_width": 1,
        })
        cur_y = cur_y + 16.0 * g_scale

        pt_gap = 14.0 * g_scale
        bullet_indent = 20.0
        pt_avail_w = (col_w - 2 * pad_x - bullet_indent) * m_ratio

        for p_idx, ptext in enumerate(col["points"]):
            ppath = f"{cpath}.points[{p_idx}]"
            pw = text_mod.wrap_lines(ptext, pt_avail_w, body_font - 1, False, max_lines=3)
            if not pw["fits"]:
                fits = False
                overflow_path = ppath

            if cur_y + pw["height"] > cy + cols_h - 16.0:
                fits = False
                overflow_path = ppath

            elements.append({
                "id": f"col-dot-{c_idx}-{p_idx}",
                "type": "circle",
                "act": 2,
                "anim": "reveal",
                "cx": cx + pad_x + 5.0,
                "cy": cur_y + (body_font - 1) * 0.58,
                "r": 4.0,
                "fill": color,
            })
            boxes.append(
                make_box(
                    f"col-pt-{c_idx}-{p_idx}",
                    "text",
                    cx + pad_x + bullet_indent,
                    cur_y,
                    max(20.0, pw["width"]),
                    pw["height"],
                    f"{cid}-pt-{p_idx}",
                    cid,
                    ppath,
                )
            )
            elements.append({
                "id": f"col-pt-{c_idx}-{p_idx}",
                "type": "text",
                "act": 2,
                "anim": "reveal",
                "lines": pw["lines"],
                "x": cx + pad_x + bullet_indent,
                "y": cur_y,
                "font_size": body_font - 1,
                "line_height": pw["line_height"],
                "fill": theme["ink"],
                "weight": 450,
            })
            cur_y = cur_y + pw["height"] + pt_gap

    if verdict:
        vy = rect["y"] + cols_h + verdict_gap
        boxes.append(make_box("verdict-bar", "shape", rect["x"], vy, rect["w"], verdict_h, "verdict-bar", None, "content.verdict"))
        elements.append({
            "id": "verdict-bar",
            "type": "rect",
            "act": 5,
            "anim": "reveal",
            "x": rect["x"],
            "y": vy,
            "w": rect["w"],
            "h": verdict_h,
            "rx": 12,
            "fill": theme["surface_alt"],
            "stroke": theme["accent"][0],
            "stroke_width": 1.5,
        })
        v_ty = vy + (verdict_h - v_wrap["height"]) / 2.0
        boxes.append(make_box("verdict-txt", "text", rect["x"] + 22.0, v_ty, max(40.0, v_wrap["width"]), v_wrap["height"], "verdict-bar", "verdict-bar", "content.verdict"))
        elements.append({
            "id": "verdict-txt",
            "type": "text",
            "act": 5,
            "anim": "reveal",
            "lines": v_wrap["lines"],
            "x": rect["x"] + 22.0,
            "y": v_ty,
            "font_size": body_font,
            "line_height": v_wrap["line_height"],
            "fill": theme["ink"],
            "weight": 700,
        })

    return {
        "fits": fits,
        "overflow_path": overflow_path,
        "adjusted_path": overflow_path,
        "boxes": boxes,
        "elements": elements,
    }

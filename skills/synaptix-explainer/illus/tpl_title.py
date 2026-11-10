"""Template: title — editorial opener / hero title card."""

from typing import Any, Dict, List


def build(
    spec: Dict[str, Any],
    chrome: Dict[str, Any],
    theme: Dict[str, Any],
    text_mod: Any,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    rect = chrome["content_rect"]
    cx = rect["x"] + rect["w"] / 2.0
    cy_mid = rect["y"] + rect["h"] / 2.0
    m_ratio = params["measure_ratio"]
    f_scale = params["font_scale"]
    g_scale = params["gap_scale"]
    scale_font = params["scale_font"]
    make_box = params["make_box"]

    content = spec["content"]
    subtitle = content.get("subtitle", "")
    icon_name = content.get("icon")
    eyebrow = spec.get("eyebrow", "")

    card_w = rect["w"]
    card_h = rect["h"]
    inner_w = (card_w - 140.0) * m_ratio

    hero_font = scale_font("hero_title", f_scale)
    sub_font = scale_font("subtitle", f_scale)

    t_wrap = text_mod.wrap_lines(spec["title"], inner_w, hero_font, True, max_lines=3)
    s_wrap = (
        text_mod.wrap_lines(subtitle, inner_w * 0.88, sub_font, False, max_lines=4)
        if subtitle
        else {"lines": [], "width": 0.0, "height": 0.0, "line_height": 28.0, "fits": True}
    )
    eb_wrap = (
        text_mod.wrap_lines(eyebrow.upper(), inner_w * 0.8, 14, True, max_lines=1)
        if eyebrow
        else {"lines": [], "width": 0.0, "height": 0.0, "line_height": 18.0, "fits": True}
    )

    fits = t_wrap["fits"] and s_wrap["fits"] and eb_wrap["fits"]
    overflow_path = "title" if not t_wrap["fits"] else ("content.subtitle" if not s_wrap["fits"] else "eyebrow")

    gap = 22.0 * g_scale
    icon_block_h = (68.0 + gap) if icon_name else 0.0
    eb_block_h = (20.0 + gap * 0.7) if eb_wrap["lines"] else 0.0
    rule_block_h = 4.0 + gap
    sub_block_h = s_wrap["height"] if s_wrap["lines"] else 0.0

    total_stack_h = icon_block_h + eb_block_h + t_wrap["height"] + gap + rule_block_h + sub_block_h
    if total_stack_h > card_h - 60.0:
        fits = False

    start_y = cy_mid - total_stack_h / 2.0
    boxes: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []

    # Subtle stage card container
    boxes.append(make_box("title-card", "shape", rect["x"], rect["y"], card_w, card_h, "hero-stage", None, "content"))
    elements.append({
        "id": "title-card",
        "type": "rect",
        "act": 1,
        "anim": "reveal",
        "x": rect["x"],
        "y": rect["y"],
        "w": card_w,
        "h": card_h,
        "rx": theme["radius"] * 1.25,
        "fill": theme["surface"],
        "stroke": theme["border"],
        "stroke_width": 1.5,
    })

    # Top accent bar inside stage
    elements.append({
        "id": "title-accent-top",
        "type": "rect",
        "act": 1,
        "anim": "reveal",
        "x": cx - 72.0,
        "y": rect["y"],
        "w": 144.0,
        "h": 5.0,
        "rx": 2.5,
        "fill": theme["accent"][0],
    })

    cur_y = start_y
    if icon_name:
        badge_r = 32.0
        boxes.append(
            make_box(
                "title-icon-badge",
                "icon",
                cx - badge_r,
                cur_y,
                badge_r * 2.0,
                badge_r * 2.0,
                "hero-icon",
                "title-card",
                "content.icon",
            )
        )
        elements.append({
            "id": "title-icon-bg",
            "type": "circle",
            "act": 2,
            "anim": "reveal",
            "cx": cx,
            "cy": cur_y + badge_r,
            "r": badge_r,
            "fill": theme["surface_alt"],
            "stroke": theme["border"],
            "stroke_width": 1.5,
        })
        elements.append({
            "id": "title-icon",
            "type": "icon",
            "act": 2,
            "anim": "reveal",
            "icon": icon_name,
            "x": cx - 16.0,
            "y": cur_y + badge_r - 16.0,
            "size": 32.0,
            "stroke": theme["accent"][0],
        })
        cur_y = cur_y + icon_block_h

    if eb_wrap["lines"]:
        ew = max(40.0, eb_wrap["width"])
        boxes.append(make_box("title-eyebrow", "text", cx - ew / 2.0, cur_y, ew, 20.0, "hero-eyebrow", "title-card", "eyebrow"))
        elements.append({
            "id": "title-eyebrow",
            "type": "text",
            "act": 1,
            "anim": "reveal",
            "lines": eb_wrap["lines"],
            "x": cx,
            "y": cur_y,
            "font_size": 14,
            "line_height": 18,
            "fill": theme["accent"][0],
            "weight": 700,
            "anchor": "middle",
            "letter_spacing": "0.1em",
        })
        cur_y = cur_y + eb_block_h

    tw = max(80.0, t_wrap["width"])
    boxes.append(make_box("title-main", "text", cx - tw / 2.0, cur_y, tw, t_wrap["height"], "hero-title", "title-card", "title"))
    elements.append({
        "id": "title-main",
        "type": "text",
        "act": 2,
        "anim": "reveal",
        "lines": t_wrap["lines"],
        "x": cx,
        "y": cur_y,
        "font_size": hero_font,
        "line_height": t_wrap["line_height"],
        "fill": theme["ink"],
        "weight": 800,
        "anchor": "middle",
    })
    cur_y = cur_y + t_wrap["height"] + gap

    # Accent divider line
    rule_w = 96.0
    boxes.append(make_box("title-rule", "shape", cx - rule_w / 2.0, cur_y, rule_w, 4.0, "hero-rule", "title-card", "title"))
    elements.append({
        "id": "title-rule",
        "type": "line",
        "act": 3,
        "anim": "draw",
        "x1": cx - rule_w / 2.0,
        "y1": cur_y + 2.0,
        "x2": cx + rule_w / 2.0,
        "y2": cur_y + 2.0,
        "stroke": theme["accent"][0],
        "stroke_width": 4,
    })
    cur_y = cur_y + rule_block_h

    if s_wrap["lines"]:
        sw = max(60.0, s_wrap["width"])
        boxes.append(make_box("title-sub", "text", cx - sw / 2.0, cur_y, sw, s_wrap["height"], "hero-subtitle", "title-card", "content.subtitle"))
        elements.append({
            "id": "title-sub",
            "type": "text",
            "act": 5,
            "anim": "reveal",
            "lines": s_wrap["lines"],
            "x": cx,
            "y": cur_y,
            "font_size": sub_font,
            "line_height": s_wrap["line_height"],
            "fill": theme["muted"],
            "weight": 450,
            "anchor": "middle",
        })

    return {
        "fits": fits,
        "overflow_path": overflow_path,
        "adjusted_path": overflow_path,
        "boxes": boxes,
        "elements": elements,
    }

"""Frame geometry, pairwise AABB collision checking, and deterministic autofit ladder."""

from typing import Any, Callable, Dict, List, Optional, Tuple

ASPECT_DIMS: Dict[str, Tuple[int, int, int]] = {
    "wide": (1280, 720, 64),
    "square": (1080, 1080, 72),
}

# Role font ladders: (default_px, min_px)
ROLE_FONTS: Dict[str, Tuple[int, int]] = {
    "hero_title": (52, 36),
    "title": (40, 32),
    "subtitle": (22, 16),
    "card_title": (20, 16),
    "body": (18, 14),
    "label": (16, 13),
}

# Autofit ladder rungs: (measure_ratio, font_scale, gap_scale, label)
AUTOFIT_RUNGS: Tuple[Tuple[float, float, float, str], ...] = (
    (1.00, 1.00, 1.00, "initial"),
    (0.92, 1.00, 1.00, "rewrap-92%"),
    (0.92, 0.90, 0.92, "font-90%"),
    (0.90, 0.82, 0.80, "font-82%-gap-80%"),
    (0.88, 0.75, 0.65, "font-75%-gap-65%"),
    (0.86, 0.70, 0.60, "min-font-gap-60%"),
)


def scale_font(role: str, font_scale: float) -> int:
    default_px, min_px = ROLE_FONTS.get(role, (18, 14))
    scaled = int(round(default_px * font_scale))
    return max(min_px, min(default_px, scaled))


def make_box(
    box_id: str,
    kind: str,
    x: float,
    y: float,
    w: float,
    h: float,
    group: str,
    parent: Optional[str] = None,
    path: str = "content",
) -> Dict[str, Any]:
    return {
        "id": box_id,
        "kind": kind,
        "x": round(float(x), 2),
        "y": round(float(y), 2),
        "w": round(max(0.0, float(w)), 2),
        "h": round(max(0.0, float(h)), 2),
        "group": group,
        "parent": parent,
        "path": path,
    }


def is_ancestor(box: Dict[str, Any], other_id: str, by_id: Dict[str, Dict[str, Any]]) -> bool:
    cur = box.get("parent")
    hops = 0
    while cur and hops < 8:
        if cur == other_id:
            return True
        parent_box = by_id.get(cur)
        cur = parent_box.get("parent") if parent_box else None
        hops = hops + 1
    return False


def check_collisions(
    boxes: List[Dict[str, Any]],
    frame_w: float,
    frame_h: float,
    pad: float = 20.0,
) -> List[Dict[str, Any]]:
    """Verify all boxes lie inside the frame and no distinct groups overlap."""
    issues: List[Dict[str, Any]] = []
    eps = 1.5
    by_id: Dict[str, Dict[str, Any]] = {}
    for b in boxes:
        by_id[b["id"]] = b

    for b in boxes:
        bx = b["x"]
        by = b["y"]
        bw = b["w"]
        bh = b["h"]
        if bx < pad - eps or by < pad - eps or (bx + bw) > (frame_w - pad + eps) or (by + bh) > (frame_h - pad + eps):
            issues.append({
                "reason": "out_of_frame",
                "box_a": b["id"],
                "box_b": "frame",
                "path": b.get("path", "content"),
            })

    n = len(boxes)
    for i in range(n):
        a = boxes[i]
        for j in range(i + 1, n):
            b = boxes[j]
            if a["group"] == b["group"]:
                continue
            if is_ancestor(a, b["id"], by_id) or is_ancestor(b, a["id"], by_id):
                continue
            overlap_x = (a["x"] + eps < b["x"] + b["w"]) and (a["x"] + a["w"] - eps > b["x"])
            overlap_y = (a["y"] + eps < b["y"] + b["h"]) and (a["y"] + a["h"] - eps > b["y"])
            if overlap_x and overlap_y:
                issues.append({
                    "reason": f"overlap ({a['kind']} vs {b['kind']})",
                    "box_a": a["id"],
                    "box_b": b["id"],
                    "path": b.get("path") or a.get("path") or "content",
                })
    return issues


def compute_chrome(
    spec: Dict[str, Any],
    text_mod: Any,
    font_scale: float = 1.0,
    measure_ratio: float = 1.0,
) -> Dict[str, Any]:
    """Lay out standard header (eyebrow + title) and footer/badge chrome, returning content rect + boxes."""
    aspect = spec["aspect"]
    width, height, margin = ASPECT_DIMS[aspect]
    is_title_tpl = spec["template"] == "title"

    boxes: List[Dict[str, Any]] = []
    inner_w = width - 2 * margin

    # Footer reserve
    has_footer_left = bool(spec["footer"] or spec["source"])
    has_badge = spec["data_kind"] == "illustrative"
    has_footer = has_footer_left or has_badge

    footer_y = height - margin + 12
    footer_h = 28 if has_footer else 0
    footer_left_text = ""
    if spec["source"] and spec["footer"]:
        footer_left_text = f"{spec['footer']} · Source: {spec['source']}"
    elif spec["source"]:
        footer_left_text = f"Source: {spec['source']}"
    elif spec["footer"]:
        footer_left_text = spec["footer"]

    badge_w = 0.0
    if has_badge:
        badge_txt = "ILLUSTRATIVE DATA"
        badge_w = round(text_mod.measure_px(badge_txt, 12, True) + 24, 2)
        bx = width - margin - badge_w
        by = height - margin - 18
        boxes.append(make_box("chrome-badge", "shape", bx, by, badge_w, 26, "chrome-badge", None, "data_kind"))
        footer_y = min(footer_y, float(by))

    footer_lines: List[str] = []
    footer_font = 13
    if footer_left_text:
        avail_footer_w = inner_w - (badge_w + 20 if has_badge else 0)
        wrapped_f = text_mod.wrap_lines(footer_left_text, avail_footer_w, footer_font, False, max_lines=2)
        footer_lines = wrapped_f["lines"][:2]
        fh = max(18.0, wrapped_f["height"])
        by_f = height - margin - fh + 6
        boxes.append(
            make_box(
                "chrome-footer",
                "text",
                margin,
                by_f,
                min(avail_footer_w, max(40.0, wrapped_f["width"])),
                fh,
                "chrome-footer",
                None,
                "source" if spec["source"] else "footer",
            )
        )
        footer_y = by_f
        footer_h = height - by_f

    # For 'title' template, the whole middle canvas owns the hero title
    if is_title_tpl:
        content_top = margin
        content_bottom = (footer_y - 20) if has_footer else (height - margin)
        return {
            "width": width,
            "height": height,
            "margin": margin,
            "eyebrow_lines": [],
            "eyebrow_y": 0.0,
            "title_lines": [],
            "title_font": 0,
            "title_y": 0.0,
            "title_fits": True,
            "footer_lines": footer_lines,
            "footer_font": footer_font,
            "footer_y": footer_y,
            "has_badge": has_badge,
            "badge_w": badge_w,
            "content_rect": {
                "x": float(margin),
                "y": float(content_top),
                "w": float(inner_w),
                "h": float(max(120.0, content_bottom - content_top)),
            },
            "boxes": boxes,
        }

    cur_y = float(margin)
    eyebrow_lines: List[str] = []
    eyebrow_y = cur_y
    if spec["eyebrow"]:
        eb_wrap = text_mod.wrap_lines(spec["eyebrow"].upper(), inner_w * measure_ratio, 13, True, max_lines=1)
        eyebrow_lines = eb_wrap["lines"]
        boxes.append(make_box("chrome-eyebrow", "text", margin, cur_y, max(40.0, eb_wrap["width"]), 18.0, "chrome-header", None, "eyebrow"))
        cur_y = cur_y + 24.0

    title_font = scale_font("title", font_scale)
    t_wrap = text_mod.wrap_lines(spec["title"], inner_w * measure_ratio, title_font, True, max_lines=2)
    title_y = cur_y
    boxes.append(
        make_box(
            "chrome-title",
            "text",
            margin,
            title_y,
            max(80.0, t_wrap["width"]),
            max(float(title_font), t_wrap["height"]),
            "chrome-header",
            None,
            "title",
        )
    )
    cur_y = cur_y + t_wrap["height"] + 26.0

    content_bottom = (footer_y - 22.0) if has_footer else float(height - margin)
    return {
        "width": width,
        "height": height,
        "margin": margin,
        "eyebrow_lines": eyebrow_lines,
        "eyebrow_y": eyebrow_y,
        "title_lines": t_wrap["lines"],
        "title_font": title_font,
        "title_line_h": t_wrap["line_height"],
        "title_y": title_y,
        "title_fits": t_wrap["fits"],
        "footer_lines": footer_lines,
        "footer_font": footer_font,
        "footer_y": footer_y,
        "has_badge": has_badge,
        "badge_w": badge_w,
        "content_rect": {
            "x": float(margin),
            "y": round(cur_y, 2),
            "w": float(inner_w),
            "h": round(max(120.0, content_bottom - cur_y), 2),
        },
        "boxes": boxes,
    }


def solve_layout(
    spec: Dict[str, Any],
    theme: Dict[str, Any],
    text_mod: Any,
    builder_fn: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    """Run template builder through the autofit ladder until fit & collision-free, or return E_NO_FIT."""
    last_failure_path = "content"
    last_reason = "Content could not fit cleanly within the frame"

    for rung_idx, (m_ratio, f_scale, g_scale, rung_label) in enumerate(AUTOFIT_RUNGS):
        chrome = compute_chrome(spec, text_mod, font_scale=f_scale, measure_ratio=m_ratio)
        params = {
            "measure_ratio": m_ratio,
            "font_scale": f_scale,
            "gap_scale": g_scale,
            "rung_index": rung_idx,
            "rung_label": rung_label,
            "scale_font": scale_font,
            "make_box": make_box,
        }
        built = builder_fn(spec, chrome, theme, text_mod, params)
        all_boxes = list(chrome["boxes"]) + list(built.get("boxes", []))

        if not chrome["title_fits"]:
            last_failure_path = "title"
            last_reason = "Title text overflows header bounds"
            continue

        if not built.get("fits", True):
            last_failure_path = built.get("overflow_path", "content")
            last_reason = built.get("overflow_reason", "Text exceeds card bounds even after wrapping")
            continue

        collisions = check_collisions(all_boxes, chrome["width"], chrome["height"], pad=20.0)
        if collisions:
            first_c = collisions[0]
            last_failure_path = first_c.get("path", "content")
            last_reason = f"Layout collision ({first_c['reason']}: {first_c['box_a']} vs {first_c['box_b']})"
            continue

        autofit_warnings: List[Dict[str, str]] = []
        if rung_idx > 0:
            adjusted_path = built.get("adjusted_path", last_failure_path)
            default_body = ROLE_FONTS["body"][0]
            used_body = scale_font("body", f_scale)
            msg = (
                f"Applied autofit step '{rung_label}' (body font {default_body}->{used_body}px)"
                if used_body != default_body
                else f"Applied autofit rewrap '{rung_label}'"
            )
            autofit_warnings.append({
                "path": adjusted_path,
                "code": "W_AUTOFIT",
                "message": msg,
                "fix": "",
            })

        return {
            "ok": True,
            "chrome": chrome,
            "elements": built.get("elements", []),
            "boxes": all_boxes,
            "warnings": autofit_warnings,
            "rung_index": rung_idx,
        }

    return {
        "ok": False,
        "error": {
            "path": last_failure_path,
            "code": "E_NO_FIT",
            "message": last_reason,
            "fix": "Shorten text in the indicated field or reduce item count",
        },
    }

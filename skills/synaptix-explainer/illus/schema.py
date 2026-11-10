"""Single-pass schema and content validator for synaptix-explainer specs."""

import json
from typing import Any, Dict, List, Optional, Tuple

MAX_SPEC_BYTES = 20480

TEMPLATES = (
    "title",
    "bar-chart",
    "line-chart",
    "donut-chart",
    "comparison",
    "process",
    "cycle",
    "timeline",
    "hub",
    "recap",
)

ROOT_KEYS = (
    "template",
    "title",
    "eyebrow",
    "footer",
    "theme",
    "aspect",
    "data_kind",
    "source",
    "content",
)

THEMES = ("paper", "ink", "light", "dark")
ASPECTS = ("wide", "square")
DATA_KINDS = ("illustrative", "sourced")


def describe_type(val: Any) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "boolean"
    if isinstance(val, (int, float)):
        return "number"
    if isinstance(val, str):
        return "string"
    if isinstance(val, list):
        return "array"
    if isinstance(val, dict):
        return "object"
    return "value"


def err(
    errors: List[Dict[str, str]],
    path: str,
    code: str,
    message: str,
    fix: str,
) -> None:
    errors.append({"path": path, "code": code, "message": message, "fix": fix})


def check_unknown_keys(
    obj: Dict[str, Any],
    allowed: Tuple[str, ...],
    prefix: str,
    errors: List[Dict[str, str]],
) -> None:
    allowed_set = set(allowed)
    valid_hint = ", ".join(allowed)
    for k in obj:
        if k not in allowed_set:
            p = f"{prefix}.{k}" if prefix else str(k)
            err(
                errors,
                p,
                "E_UNKNOWN_KEY",
                f"Unknown key '{k}'",
                f"Remove '{k}'. Allowed keys here: {valid_hint}",
            )


def check_str(
    val: Any,
    path: str,
    max_len: int,
    required: bool,
    errors: List[Dict[str, str]],
) -> str:
    if val is None:
        if required:
            err(errors, path, "E_MISSING", f"Missing required text at '{path}'", f"Set '{path}' (<= {max_len} chars)")
        return ""
    if not isinstance(val, str):
        err(errors, path, "E_TYPE", f"Expected string at '{path}', got {describe_type(val)}", "Provide a plain text string")
        return ""
    cleaned = " ".join(val.strip().split())
    if required and not cleaned:
        err(errors, path, "E_MISSING", f"'{path}' cannot be empty", f"Provide non-empty text (<= {max_len} chars)")
        return ""
    if len(cleaned) > max_len:
        err(
            errors,
            path,
            "E_TEXT_TOO_LONG",
            f"'{path}' is {len(cleaned)} chars (max {max_len})",
            f"Rewrite shorter to <= {max_len} characters without cutting words mid-sentence",
        )
    return cleaned


def check_icon(
    val: Any,
    path: str,
    icons_mod: Any,
    errors: List[Dict[str, str]],
) -> Optional[str]:
    if val is None or val == "":
        return None
    if not isinstance(val, str):
        err(errors, path, "E_TYPE", "Icon id must be a string", icons_mod.valid_icons_hint())
        return None
    name = val.strip().lower()
    if not icons_mod.is_valid_icon(name):
        err(
            errors,
            path,
            "E_UNKNOWN_ICON",
            f"Unknown icon '{val}'",
            icons_mod.valid_icons_hint(),
        )
        return None
    return name


def check_num(
    raw_val: Any,
    path: str,
    calc_mod: Any,
    errors: List[Dict[str, str]],
    min_val: Optional[float] = None,
    strict_gt: Optional[float] = None,
) -> Optional[float]:
    if raw_val is None:
        err(errors, path, "E_MISSING", f"Missing numeric value at '{path}'", "Provide a number or arithmetic like 12*4")
        return None
    try:
        num = calc_mod.eval_value(raw_val)
    except Exception as exc:
        code = exc.code if hasattr(exc, "code") else "E_CALC_SYNTAX"
        msg = exc.message if hasattr(exc, "message") else str(exc)
        fix = exc.fix if hasattr(exc, "fix") else "Use a plain number or simple arithmetic"
        err(errors, path, code, msg, fix)
        return None

    fval = float(num)
    if min_val is not None and fval < min_val:
        err(
            errors,
            path,
            "E_CALC_RANGE",
            f"Value {fval} must be >= {min_val}",
            f"Provide a value >= {min_val}",
        )
        return None
    if strict_gt is not None and fval <= strict_gt:
        err(
            errors,
            path,
            "E_CALC_RANGE",
            f"Value {fval} must be > {strict_gt}",
            f"Provide a positive value > {strict_gt}",
        )
        return None
    return fval


def check_list_bounds(
    raw_list: Any,
    path: str,
    min_items: int,
    max_items: int,
    errors: List[Dict[str, str]],
) -> Optional[List[Any]]:
    if raw_list is None:
        err(errors, path, "E_MISSING", f"Missing required list '{path}'", f"Provide {min_items} to {max_items} items")
        return None
    if not isinstance(raw_list, list):
        err(errors, path, "E_TYPE", f"Expected list at '{path}', got {describe_type(raw_list)}", f"Pass an array of {min_items}..{max_items} items")
        return None
    if len(raw_list) < min_items or len(raw_list) > max_items:
        err(
            errors,
            path,
            "E_LIMIT_ITEMS",
            f"'{path}' has {len(raw_list)} items (allowed {min_items}..{max_items})",
            f"Keep between {min_items} and {max_items} items",
        )
    return raw_list


def validate_spec(
    raw_spec: Any,
    calc_mod: Any,
    icons_mod: Any,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
    """Validate spec in one pass, returning (normalized_spec | None, errors, warnings)."""
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    if not isinstance(raw_spec, dict):
        err(errors, "", "E_TYPE", "Spec must be a JSON object", "Pass spec as a JSON object with template, title, and content")
        return None, errors, warnings

    try:
        encoded_len = len(json.dumps(raw_spec).encode("utf-8"))
    except Exception:
        err(errors, "", "E_TYPE", "Spec is not JSON-serializable", "Ensure spec contains valid JSON primitives")
        return None, errors, warnings

    if encoded_len > MAX_SPEC_BYTES:
        err(
            errors,
            "",
            "E_SIZE",
            f"Spec size {encoded_len} bytes exceeds {MAX_SPEC_BYTES}-byte limit",
            "Trim items or text to fit within 20 KB",
        )
        return None, errors, warnings

    check_unknown_keys(raw_spec, ROOT_KEYS, "", errors)

    tpl = raw_spec.get("template")
    if tpl is None or tpl == "":
        err(errors, "template", "E_MISSING", "Missing 'template'", "Choose one of: " + ", ".join(TEMPLATES))
        tpl_str = ""
    elif not isinstance(tpl, str):
        err(errors, "template", "E_TYPE", "'template' must be a string", "Choose one of: " + ", ".join(TEMPLATES))
        tpl_str = ""
    elif tpl not in TEMPLATES:
        err(
            errors,
            "template",
            "E_UNKNOWN_TEMPLATE",
            f"Unknown template '{tpl}'",
            "Choose one of: " + ", ".join(TEMPLATES),
        )
        tpl_str = ""
    else:
        tpl_str = tpl

    title = check_str(raw_spec.get("title"), "title", 60, True, errors)
    eyebrow = check_str(raw_spec.get("eyebrow"), "eyebrow", 40, False, errors)
    footer = check_str(raw_spec.get("footer"), "footer", 70, False, errors)

    raw_theme = raw_spec.get("theme", "paper")
    if raw_theme is None:
        theme = "paper"
    elif not isinstance(raw_theme, str) or raw_theme not in THEMES:
        err(errors, "theme", "E_TYPE", f"Invalid theme '{raw_theme}'", "Use one of: paper, ink, light, dark")
        theme = "paper"
    else:
        theme = raw_theme

    raw_aspect = raw_spec.get("aspect", "wide")
    if raw_aspect is None:
        aspect = "wide"
    elif not isinstance(raw_aspect, str) or raw_aspect not in ASPECTS:
        err(errors, "aspect", "E_TYPE", f"Invalid aspect '{raw_aspect}'", "Use 'wide' (1280x720) or 'square' (1080x1080)")
        aspect = "wide"
    else:
        aspect = raw_aspect

    raw_dk = raw_spec.get("data_kind", "illustrative")
    if raw_dk is None:
        data_kind = "illustrative"
    elif not isinstance(raw_dk, str) or raw_dk not in DATA_KINDS:
        err(errors, "data_kind", "E_TYPE", f"Invalid data_kind '{raw_dk}'", "Use 'illustrative' or 'sourced'")
        data_kind = "illustrative"
    else:
        data_kind = raw_dk

    raw_source = raw_spec.get("source")
    if data_kind == "sourced":
        if raw_source is None or (isinstance(raw_source, str) and not raw_source.strip()):
            err(
                errors,
                "source",
                "E_SOURCE_REQUIRED",
                "'source' is required when data_kind is 'sourced'",
                "Set 'source' (<= 90 chars) citing the origin, or set data_kind to 'illustrative'",
            )
            source = ""
        else:
            source = check_str(raw_source, "source", 90, True, errors)
    else:
        source = check_str(raw_source, "source", 90, False, errors)

    raw_content = raw_spec.get("content")
    if raw_content is None:
        err(errors, "content", "E_MISSING", "Missing 'content' object", "Provide the template-specific 'content' object")
        return None, errors, warnings
    if not isinstance(raw_content, dict):
        err(errors, "content", "E_TYPE", "'content' must be an object", "Pass 'content' as a JSON dictionary")
        return None, errors, warnings

    norm_content: Dict[str, Any] = {}
    if tpl_str:
        norm_content = validate_template_content(tpl_str, raw_content, calc_mod, icons_mod, errors)

    if errors:
        return None, errors, warnings

    if data_kind == "illustrative" and tpl_str in ("bar-chart", "line-chart", "donut-chart"):
        warnings.append({
            "path": "data_kind",
            "code": "W_ILLUSTRATIVE_BADGE",
            "message": "Illustrative badge shown because data_kind is 'illustrative'",
            "fix": "",
        })

    normalized = {
        "template": tpl_str,
        "title": title,
        "eyebrow": eyebrow,
        "footer": footer,
        "theme": theme,
        "aspect": aspect,
        "data_kind": data_kind,
        "source": source,
        "content": norm_content,
    }
    return normalized, errors, warnings


def validate_template_content(
    tpl: str,
    content: Dict[str, Any],
    calc_mod: Any,
    icons_mod: Any,
    errors: List[Dict[str, str]],
) -> Dict[str, Any]:
    if tpl == "title":
        check_unknown_keys(content, ("subtitle", "icon"), "content", errors)
        return {
            "subtitle": check_str(content.get("subtitle"), "content.subtitle", 100, False, errors),
            "icon": check_icon(content.get("icon"), "content.icon", icons_mod, errors),
        }

    if tpl == "bar-chart":
        check_unknown_keys(content, ("items", "y_label"), "content", errors)
        y_label = check_str(content.get("y_label"), "content.y_label", 32, False, errors)
        raw_items = check_list_bounds(content.get("items"), "content.items", 2, 8, errors)
        items: List[Dict[str, Any]] = []
        if raw_items is not None:
            for idx, it in enumerate(raw_items):
                ipath = f"content.items[{idx}]"
                if not isinstance(it, dict):
                    err(errors, ipath, "E_TYPE", "Each bar item must be an object", "Use {label, value, unit?}")
                    continue
                check_unknown_keys(it, ("label", "value", "unit"), ipath, errors)
                lbl = check_str(it.get("label"), f"{ipath}.label", 18, True, errors)
                val = check_num(it.get("value"), f"{ipath}.value", calc_mod, errors, min_val=0.0)
                unit = check_str(it.get("unit"), f"{ipath}.unit", 10, False, errors)
                if val is not None:
                    items.append({"label": lbl, "value": val, "unit": unit})
        return {"items": items, "y_label": y_label}

    if tpl == "line-chart":
        check_unknown_keys(content, ("series", "y_label"), "content", errors)
        y_label = check_str(content.get("y_label"), "content.y_label", 32, False, errors)
        raw_series = check_list_bounds(content.get("series"), "content.series", 1, 3, errors)
        series_out: List[Dict[str, Any]] = []
        expected_len: Optional[int] = None
        if raw_series is not None:
            for s_idx, ser in enumerate(raw_series):
                spath = f"content.series[{s_idx}]"
                if not isinstance(ser, dict):
                    err(errors, spath, "E_TYPE", "Each series must be an object", "Use {name, points:[{x, y}]}")
                    continue
                check_unknown_keys(ser, ("name", "points"), spath, errors)
                sname = check_str(ser.get("name"), f"{spath}.name", 24, True, errors)
                raw_pts = check_list_bounds(ser.get("points"), f"{spath}.points", 3, 12, errors)
                pts_out: List[Dict[str, Any]] = []
                if raw_pts is not None:
                    if expected_len is None:
                        expected_len = len(raw_pts)
                    elif len(raw_pts) != expected_len:
                        err(
                            errors,
                            f"{spath}.points",
                            "E_LIMIT_ITEMS",
                            f"Series has {len(raw_pts)} points; expected {expected_len} to match series[0]",
                            "Give every series the same number of points",
                        )
                    for p_idx, pt in enumerate(raw_pts):
                        ppath = f"{spath}.points[{p_idx}]"
                        if not isinstance(pt, dict):
                            err(errors, ppath, "E_TYPE", "Each point must be an object", "Use {x, y}")
                            continue
                        check_unknown_keys(pt, ("x", "y"), ppath, errors)
                        raw_x = pt.get("x")
                        if isinstance(raw_x, (int, float)) and not isinstance(raw_x, bool):
                            x_str = check_str(str(raw_x), f"{ppath}.x", 10, True, errors)
                        else:
                            x_str = check_str(raw_x, f"{ppath}.x", 10, True, errors)
                        y_val = check_num(pt.get("y"), f"{ppath}.y", calc_mod, errors)
                        if y_val is not None:
                            pts_out.append({"x": x_str, "y": y_val})
                series_out.append({"name": sname, "points": pts_out})
        return {"series": series_out, "y_label": y_label}

    if tpl == "donut-chart":
        check_unknown_keys(content, ("items", "center_label"), "content", errors)
        center_label = check_str(content.get("center_label"), "content.center_label", 24, False, errors)
        raw_items = check_list_bounds(content.get("items"), "content.items", 2, 6, errors)
        items_out: List[Dict[str, Any]] = []
        total = 0.0
        if raw_items is not None:
            for idx, it in enumerate(raw_items):
                ipath = f"content.items[{idx}]"
                if not isinstance(it, dict):
                    err(errors, ipath, "E_TYPE", "Each donut slice must be an object", "Use {label, value}")
                    continue
                check_unknown_keys(it, ("label", "value"), ipath, errors)
                lbl = check_str(it.get("label"), f"{ipath}.label", 20, True, errors)
                val = check_num(it.get("value"), f"{ipath}.value", calc_mod, errors, strict_gt=0.0)
                if val is not None:
                    total = total + val
                    items_out.append({"label": lbl, "value": val})
            if raw_items and items_out and total <= 0.0:
                err(errors, "content.items", "E_CALC_RANGE", "Total of donut slices must be > 0", "Provide positive slice values")
        return {"items": items_out, "center_label": center_label}

    if tpl == "comparison":
        check_unknown_keys(content, ("columns", "verdict"), "content", errors)
        verdict = check_str(content.get("verdict"), "content.verdict", 80, False, errors)
        raw_cols = check_list_bounds(content.get("columns"), "content.columns", 2, 3, errors)
        cols_out: List[Dict[str, Any]] = []
        if raw_cols is not None:
            for c_idx, col in enumerate(raw_cols):
                cpath = f"content.columns[{c_idx}]"
                if not isinstance(col, dict):
                    err(errors, cpath, "E_TYPE", "Each column must be an object", "Use {title, points:[...], icon?}")
                    continue
                check_unknown_keys(col, ("title", "points", "icon"), cpath, errors)
                ctitle = check_str(col.get("title"), f"{cpath}.title", 28, True, errors)
                cicon = check_icon(col.get("icon"), f"{cpath}.icon", icons_mod, errors)
                raw_pts = check_list_bounds(col.get("points"), f"{cpath}.points", 2, 5, errors)
                pts_clean: List[str] = []
                if raw_pts is not None:
                    for p_idx, pval in enumerate(raw_pts):
                        pts_clean.append(check_str(pval, f"{cpath}.points[{p_idx}]", 60, True, errors))
                cols_out.append({"title": ctitle, "points": pts_clean, "icon": cicon})
        return {"columns": cols_out, "verdict": verdict}

    if tpl == "process":
        check_unknown_keys(content, ("steps",), "content", errors)
        raw_steps = check_list_bounds(content.get("steps"), "content.steps", 3, 6, errors)
        steps_out: List[Dict[str, Any]] = []
        if raw_steps is not None:
            for idx, st in enumerate(raw_steps):
                spath = f"content.steps[{idx}]"
                if not isinstance(st, dict):
                    err(errors, spath, "E_TYPE", "Each step must be an object", "Use {title, detail?, icon?}")
                    continue
                check_unknown_keys(st, ("title", "detail", "icon"), spath, errors)
                stitle = check_str(st.get("title"), f"{spath}.title", 28, True, errors)
                sdetail = check_str(st.get("detail"), f"{spath}.detail", 80, False, errors)
                sicon = check_icon(st.get("icon"), f"{spath}.icon", icons_mod, errors)
                steps_out.append({"title": stitle, "detail": sdetail, "icon": sicon})
        return {"steps": steps_out}

    if tpl == "cycle":
        check_unknown_keys(content, ("stages", "center"), "content", errors)
        center = check_str(content.get("center"), "content.center", 28, False, errors)
        raw_stages = check_list_bounds(content.get("stages"), "content.stages", 3, 6, errors)
        stages_out: List[Dict[str, Any]] = []
        if raw_stages is not None:
            for idx, st in enumerate(raw_stages):
                spath = f"content.stages[{idx}]"
                if not isinstance(st, dict):
                    err(errors, spath, "E_TYPE", "Each stage must be an object", "Use {title, detail?}")
                    continue
                check_unknown_keys(st, ("title", "detail"), spath, errors)
                stitle = check_str(st.get("title"), f"{spath}.title", 28, True, errors)
                sdetail = check_str(st.get("detail"), f"{spath}.detail", 80, False, errors)
                stages_out.append({"title": stitle, "detail": sdetail})
        return {"stages": stages_out, "center": center}

    if tpl == "timeline":
        check_unknown_keys(content, ("events",), "content", errors)
        raw_events = check_list_bounds(content.get("events"), "content.events", 3, 7, errors)
        events_out: List[Dict[str, Any]] = []
        if raw_events is not None:
            for idx, ev in enumerate(raw_events):
                epath = f"content.events[{idx}]"
                if not isinstance(ev, dict):
                    err(errors, epath, "E_TYPE", "Each event must be an object", "Use {when, title, detail?}")
                    continue
                check_unknown_keys(ev, ("when", "title", "detail"), epath, errors)
                ewhen = check_str(ev.get("when"), f"{epath}.when", 12, True, errors)
                etitle = check_str(ev.get("title"), f"{epath}.title", 28, True, errors)
                edetail = check_str(ev.get("detail"), f"{epath}.detail", 70, False, errors)
                events_out.append({"when": ewhen, "title": etitle, "detail": edetail})
        return {"events": events_out}

    if tpl == "hub":
        check_unknown_keys(content, ("center", "spokes"), "content", errors)
        raw_center = content.get("center")
        center_obj = {"title": "", "detail": ""}
        if raw_center is None:
            err(errors, "content.center", "E_MISSING", "Missing 'content.center'", "Provide {title, detail?}")
        elif not isinstance(raw_center, dict):
            err(errors, "content.center", "E_TYPE", "'content.center' must be an object", "Provide {title, detail?}")
        else:
            check_unknown_keys(raw_center, ("title", "detail"), "content.center", errors)
            center_obj = {
                "title": check_str(raw_center.get("title"), "content.center.title", 28, True, errors),
                "detail": check_str(raw_center.get("detail"), "content.center.detail", 80, False, errors),
            }

        raw_spokes = check_list_bounds(content.get("spokes"), "content.spokes", 3, 6, errors)
        spokes_out: List[Dict[str, Any]] = []
        if raw_spokes is not None:
            for idx, sp in enumerate(raw_spokes):
                spath = f"content.spokes[{idx}]"
                if not isinstance(sp, dict):
                    err(errors, spath, "E_TYPE", "Each spoke must be an object", "Use {title, detail?, icon?}")
                    continue
                check_unknown_keys(sp, ("title", "detail", "icon"), spath, errors)
                stitle = check_str(sp.get("title"), f"{spath}.title", 28, True, errors)
                sdetail = check_str(sp.get("detail"), f"{spath}.detail", 80, False, errors)
                sicon = check_icon(sp.get("icon"), f"{spath}.icon", icons_mod, errors)
                spokes_out.append({"title": stitle, "detail": sdetail, "icon": sicon})
        return {"center": center_obj, "spokes": spokes_out}

    if tpl == "recap":
        check_unknown_keys(content, ("points",), "content", errors)
        raw_pts = check_list_bounds(content.get("points"), "content.points", 2, 5, errors)
        pts_out2: List[Dict[str, Any]] = []
        if raw_pts is not None:
            for idx, pt in enumerate(raw_pts):
                ppath = f"content.points[{idx}]"
                if not isinstance(pt, dict):
                    err(errors, ppath, "E_TYPE", "Each recap point must be an object", "Use {title, detail?}")
                    continue
                check_unknown_keys(pt, ("title", "detail"), ppath, errors)
                ptitle = check_str(pt.get("title"), f"{ppath}.title", 36, True, errors)
                pdetail = check_str(pt.get("detail"), f"{ppath}.detail", 90, False, errors)
                pts_out2.append({"title": ptitle, "detail": pdetail})
        return {"points": pts_out2}

    return {}

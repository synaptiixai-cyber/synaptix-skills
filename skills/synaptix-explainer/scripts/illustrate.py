"""Entry-point script for synaptix-explainer (executed inside SkillScriptRunner)."""

import json
from typing import Any, Callable, Dict, List

from illus import (
    calc,
    icons,
    layout,
    render,
    schema,
    text,
    themes,
    tpl_bar,
    tpl_comparison,
    tpl_cycle,
    tpl_donut,
    tpl_hub,
    tpl_line,
    tpl_process,
    tpl_recap,
    tpl_timeline,
    tpl_title,
)

BUILDERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "title": tpl_title.build,
    "bar-chart": tpl_bar.build,
    "line-chart": tpl_line.build,
    "donut-chart": tpl_donut.build,
    "comparison": tpl_comparison.build,
    "process": tpl_process.build,
    "cycle": tpl_cycle.build,
    "timeline": tpl_timeline.build,
    "hub": tpl_hub.build,
    "recap": tpl_recap.build,
}

TEMPLATE_LABELS: Dict[str, str] = {
    "title": "Title card",
    "bar-chart": "Bar chart",
    "line-chart": "Line chart",
    "donut-chart": "Donut chart",
    "comparison": "Comparison",
    "process": "Process flow",
    "cycle": "Cycle diagram",
    "timeline": "Timeline",
    "hub": "Hub diagram",
    "recap": "Recap card",
}


def build_summary(spec: Dict[str, Any]) -> str:
    tpl = spec["template"]
    label = TEMPLATE_LABELS.get(tpl, tpl)
    content = spec["content"]
    detail = ""
    if tpl == "bar-chart":
        detail = f"{len(content['items'])} bars"
    elif tpl == "line-chart":
        n_ser = len(content["series"])
        n_pts = len(content["series"][0]["points"]) if content["series"] else 0
        detail = f"{n_ser} series, {n_pts} points"
    elif tpl == "donut-chart":
        detail = f"{len(content['items'])} slices"
    elif tpl == "comparison":
        detail = f"{len(content['columns'])} options"
    elif tpl == "process":
        detail = f"{len(content['steps'])} steps"
    elif tpl == "cycle":
        detail = f"{len(content['stages'])} stages"
    elif tpl == "timeline":
        detail = f"{len(content['events'])} milestones"
    elif tpl == "hub":
        detail = f"center + {len(content['spokes'])} spokes"
    elif tpl == "recap":
        detail = f"{len(content['points'])} takeaways"

    qualifiers: List[str] = []
    if detail:
        qualifiers.append(detail)
    qualifiers.append(spec["data_kind"])
    qual_str = ", ".join(qualifiers)
    return f"{label}: {spec['title']} ({qual_str})."


def execute(raw_inputs: Any) -> Dict[str, Any]:
    include_svg = False
    theme_overrides: Any = None
    raw_spec: Any = raw_inputs

    if isinstance(raw_inputs, dict):
        include_svg = bool(raw_inputs.get("include_svg", False))
        theme_overrides = raw_inputs.get("theme_overrides")
        if "spec" in raw_inputs:
            raw_spec = raw_inputs["spec"]
        else:
            # Allow passing spec keys directly if caller omitted the outer 'spec' wrapper
            passthrough: Dict[str, Any] = {}
            for k, v in raw_inputs.items():
                if k not in ("include_svg", "theme_overrides"):
                    passthrough[k] = v
            raw_spec = passthrough

    if isinstance(raw_spec, str):
        try:
            raw_spec = json.loads(raw_spec)
        except Exception:
            return {
                "errors": [
                    {
                        "path": "",
                        "code": "E_TYPE",
                        "message": "Spec string is not valid JSON",
                        "fix": "Pass 'spec' as a parsed JSON object",
                    }
                ],
                "warnings": [],
            }

    spec, errors, warnings = schema.validate_spec(raw_spec, calc, icons)
    if errors or spec is None:
        return {"errors": errors, "warnings": warnings}

    theme = themes.resolve_theme(spec["theme"], warnings, custom_overrides=theme_overrides)
    builder_fn = BUILDERS[spec["template"]]
    solved = layout.solve_layout(spec, theme, text, builder_fn)
    if not solved["ok"]:
        return {"errors": [solved["error"]], "warnings": warnings}

    summary_text = build_summary(spec)
    svg_markup, html_doc, duration_s = render.build_svg_and_html(
        spec,
        solved,
        theme,
        icons,
        summary_text,
    )

    out: Dict[str, Any] = {
        "html_app": html_doc,
        "summary": summary_text,
        "warnings": warnings + solved["warnings"],
        "meta": {
            "template": spec["template"],
            "theme": spec["theme"],
            "aspect": spec["aspect"],
            "width": solved["chrome"]["width"],
            "height": solved["chrome"]["height"],
            "duration_s": duration_s,
            "data_kind": spec["data_kind"],
        },
    }
    if include_svg:
        out["svg"] = svg_markup
    return out


result = execute(inputs)

"""Minimal stroke icon set for synaptix-explainer (12 vector icons, 24x24 viewBox)."""

import html
from typing import Dict, Tuple

VALID_ICONS: Tuple[str, ...] = (
    "check",
    "bolt",
    "shield",
    "clock",
    "cloud",
    "database",
    "user",
    "chart",
    "gear",
    "globe",
    "lock",
    "star",
)

ICON_PATHS: Dict[str, str] = {
    "check": '<path d="M20 6L9 17l-5-5"/>',
    "bolt": '<path d="M13 2L4 14h7l-1 8 10-12h-7l0-8z"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
    "cloud": '<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>',
    "database": (
        '<ellipse cx="12" cy="5" rx="8" ry="3"/>'
        '<path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5"/>'
        '<path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3"/>'
    ),
    "user": (
        '<circle cx="12" cy="8" r="4"/>'
        '<path d="M20 21a8 8 0 0 0-16 0"/>'
    ),
    "chart": '<path d="M18 20V10M12 20V4M6 20v-6"/>',
    "gear": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M12 2v3M12 19v3M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12'
        'M2 12h3M19 12h3M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12"/>'
    ),
    "globe": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>'
    ),
    "lock": (
        '<rect x="5" y="11" width="14" height="10" rx="2"/>'
        '<path d="M8 11V7a4 4 0 0 1 8 0v4"/>'
    ),
    "star": (
        '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 '
        '18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
    ),
}


def is_valid_icon(name: str) -> bool:
    return name in ICON_PATHS


def valid_icons_hint() -> str:
    return "Use one of: " + ", ".join(VALID_ICONS)


def render_icon(
    name: str,
    x: float,
    y: float,
    size: float,
    stroke: str,
    elem_id: str = "",
    cls: str = "",
    delay_s: float = 0.0,
) -> str:
    """Render a 24x24 stroke icon positioned with top-left at (x, y) and scaled to size."""
    body = ICON_PATHS.get(name, "")
    if not body:
        return ""
    scale = round(size / 24.0, 4)
    tx = round(x, 2)
    ty = round(y, 2)
    esc_stroke = html.escape(stroke, quote=True)
    id_attr = f' id="{html.escape(elem_id, quote=True)}"' if elem_id else ""
    cls_attr = f' class="{html.escape(cls, quote=True)}"' if cls else ""
    style_attr = f' style="--d:{delay_s:.2f}s"' if cls else ""
    return (
        f'<g{id_attr}{cls_attr}{style_attr} '
        f'transform="translate({tx},{ty}) scale({scale})" '
        f'fill="none" stroke="{esc_stroke}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</g>'
    )

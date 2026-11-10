"""Editorial color & motion themes with deterministic WCAG 2.1 AA (4.5:1) contrast enforcement."""

from typing import Any, Dict, List, Tuple

FONT_STACK = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
VALID_THEMES = ("paper", "ink", "light", "dark")

RAW_THEMES: Dict[str, Dict[str, Any]] = {
    "paper": {
        "name": "paper",
        "is_dark": False,
        "bg": "#FAF7F2",
        "surface": "#FFFFFF",
        "surface_alt": "#F3EDE2",
        "ink": "#1C1917",
        "muted": "#57534E",
        "grid": "#E5DEC9",
        "border": "#DDD5C4",
        "accent": ["#C2410C", "#0F766E", "#1D4ED8", "#7C3AED", "#B45309"],
        "font": FONT_STACK,
        "radius": 16,
        "motion": {"ease": "cubic-bezier(0.22, 1, 0.36, 1)", "step_ms": 90},
    },
    "ink": {
        "name": "ink",
        "is_dark": True,
        "bg": "#0F172A",
        "surface": "#1E293B",
        "surface_alt": "#162033",
        "ink": "#F8FAFC",
        "muted": "#94A3B8",
        "grid": "#334155",
        "border": "#334155",
        "accent": ["#38BDF8", "#34D399", "#FBBF24", "#A78BFA", "#FB7185"],
        "font": FONT_STACK,
        "radius": 14,
        "motion": {"ease": "cubic-bezier(0.16, 1, 0.3, 1)", "step_ms": 75},
    },
    "light": {
        "name": "light",
        "is_dark": False,
        "bg": "#F8FAFC",
        "surface": "#FFFFFF",
        "surface_alt": "#F1F5F9",
        "ink": "#0F172A",
        "muted": "#475569",
        "grid": "#E2E8F0",
        "border": "#CBD5E1",
        "accent": ["#2563EB", "#0D9488", "#D97706", "#7C3AED", "#E11D48"],
        "font": FONT_STACK,
        "radius": 14,
        "motion": {"ease": "cubic-bezier(0.2, 0.9, 0.3, 1)", "step_ms": 85},
    },
    "dark": {
        "name": "dark",
        "is_dark": True,
        "bg": "#090D16",
        "surface": "#111827",
        "surface_alt": "#1A2333",
        "ink": "#F3F4F6",
        "muted": "#9CA3AF",
        "grid": "#1F2937",
        "border": "#283548",
        "accent": ["#60A5FA", "#2DD4BF", "#F59E0B", "#C084FC", "#F472B6"],
        "font": FONT_STACK,
        "radius": 14,
        "motion": {"ease": "cubic-bezier(0.18, 0.95, 0.32, 1)", "step_ms": 80},
    },
}


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    r = max(0, min(255, int(round(rgb[0]))))
    g = max(0, min(255, int(round(rgb[1]))))
    b = max(0, min(255, int(round(rgb[2]))))
    return f"#{r:02X}{g:02X}{b:02X}"


def channel_lum(c: int) -> float:
    s = c / 255.0
    if s <= 0.04045:
        return s / 12.92
    return ((s + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    return 0.2126 * channel_lum(rgb[0]) + 0.7152 * channel_lum(rgb[1]) + 0.0722 * channel_lum(rgb[2])


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    l1 = relative_luminance(hex_to_rgb(fg_hex))
    l2 = relative_luminance(hex_to_rgb(bg_hex))
    hi = max(l1, l2)
    lo = min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def ensure_aa_contrast(fg_hex: str, bg_hex: str, min_ratio: float = 4.5) -> Tuple[str, bool]:
    """Adjust fg_hex toward pure black or white if contrast with bg_hex is < min_ratio."""
    if contrast_ratio(fg_hex, bg_hex) >= min_ratio:
        return fg_hex, False

    fg_rgb = hex_to_rgb(fg_hex)
    toward_white = contrast_ratio("#FFFFFF", bg_hex) >= contrast_ratio("#000000", bg_hex)
    target = (255, 255, 255) if toward_white else (0, 0, 0)

    for step in range(1, 33):
        t = step / 32.0
        cand_rgb = (
            int(round(fg_rgb[0] + (target[0] - fg_rgb[0]) * t)),
            int(round(fg_rgb[1] + (target[1] - fg_rgb[1]) * t)),
            int(round(fg_rgb[2] + (target[2] - fg_rgb[2]) * t)),
        )
        cand_hex = rgb_to_hex(cand_rgb)
        if contrast_ratio(cand_hex, bg_hex) >= min_ratio:
            return cand_hex, True

    return ("#FFFFFF" if toward_white else "#000000"), True


def text_on_fill(fill_hex: str) -> str:
    """Choose crisp white or dark ink text on top of an accent fill."""
    return "#FFFFFF" if contrast_ratio("#FFFFFF", fill_hex) >= contrast_ratio("#0F172A", fill_hex) else "#0F172A"


def tint_hex(accent_hex: str, bg_hex: str, alpha: float = 0.14) -> str:
    """Blend accent_hex onto bg_hex for soft pill/header backgrounds."""
    a_rgb = hex_to_rgb(accent_hex)
    b_rgb = hex_to_rgb(bg_hex)
    mixed = (
        int(round(b_rgb[0] + (a_rgb[0] - b_rgb[0]) * alpha)),
        int(round(b_rgb[1] + (a_rgb[1] - b_rgb[1]) * alpha)),
        int(round(b_rgb[2] + (a_rgb[2] - b_rgb[2]) * alpha)),
    )
    return rgb_to_hex(mixed)


def resolve_theme(name: str, warnings: List[Dict[str, str]], custom_overrides: Any = None) -> Dict[str, Any]:
    """Return a validated copy of the requested theme, checking AA contrast."""
    base = RAW_THEMES.get(name, RAW_THEMES["paper"])
    tk: Dict[str, Any] = {
        "name": base["name"],
        "is_dark": base["is_dark"],
        "bg": base["bg"],
        "surface": base["surface"],
        "surface_alt": base["surface_alt"],
        "ink": base["ink"],
        "muted": base["muted"],
        "grid": base["grid"],
        "border": base["border"],
        "accent": list(base["accent"]),
        "font": base["font"],
        "radius": base["radius"],
        "motion": dict(base["motion"]),
    }
    if isinstance(custom_overrides, dict):
        for k in ("ink", "muted", "bg", "surface"):
            if isinstance(custom_overrides.get(k), str):
                tk[k] = custom_overrides[k]

    for role in ("ink", "muted"):
        for bg_key in ("bg", "surface"):
            fixed_hex, changed = ensure_aa_contrast(tk[role], tk[bg_key], 4.5)
            if changed:
                old_hex = tk[role]
                tk[role] = fixed_hex
                warnings.append({
                    "path": f"theme.{role}",
                    "code": "W_CONTRAST_FIXED",
                    "message": f"Adjusted {role} {old_hex}->{fixed_hex} to meet 4.5:1 AA contrast on {bg_key}",
                    "fix": "",
                })
    return tk

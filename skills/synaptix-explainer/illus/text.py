"""Conservative character-class text measurement, wrapping, and number formatting."""

import math
from typing import Any, Dict, List, Optional

NARROW_28 = frozenset("ilI.,':;!|")
NARROW_38 = frozenset("ftjr()[]-")
WIDE_85 = frozenset("mwMW@%")
UPPER_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGIT_CHARS = frozenset("0123456789")

BOLD_FACTOR = 1.06
SAFETY_FACTOR = 1.08


def is_wide_codepoint(code: int) -> bool:
    """Detect East Asian Wide / Fullwidth / Emoji codepoints without unicodedata."""
    if code < 0x1100:
        return False
    return (
        (0x1100 <= code <= 0x115F)
        or (0x2E80 <= code <= 0xA4CF)
        or (0xAC00 <= code <= 0xD7A3)
        or (0xF900 <= code <= 0xFAFF)
        or (0xFE10 <= code <= 0xFE6F)
        or (0xFF01 <= code <= 0xFF60)
        or (0xFFE0 <= code <= 0xFFE6)
        or (0x1F300 <= code <= 0x1FAFF)
        or (0x20000 <= code <= 0x3FFFD)
    )


def char_em_width(ch: str) -> float:
    if ch == " ":
        return 0.30
    if ch in NARROW_28:
        return 0.28
    if ch in NARROW_38:
        return 0.38
    if ch in WIDE_85:
        return 0.85
    if ch in UPPER_CHARS:
        return 0.66
    if ch in DIGIT_CHARS:
        return 0.56
    if is_wide_codepoint(ord(ch)):
        return 1.00
    return 0.52


def measure_px(text: str, font_px: float, bold: bool = False) -> float:
    """Estimated rendered pixel width using conservative character-class widths."""
    if not text:
        return 0.0
    em_sum = 0.0
    for ch in text:
        em_sum = em_sum + char_em_width(ch)
    mult = SAFETY_FACTOR * (BOLD_FACTOR if bold else 1.0)
    return em_sum * font_px * mult


def break_long_token(token: str, max_width_px: float, font_px: float, bold: bool) -> List[str]:
    """Hard-break a single token that exceeds max_width_px."""
    chunks: List[str] = []
    cur = ""
    for ch in token:
        trial = cur + ch
        if cur and measure_px(trial, font_px, bold) > max_width_px:
            chunks.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        chunks.append(cur)
    return chunks or [token]


def split_wrap_units(cleaned: str) -> List[Any]:
    """Split text into (unit_str, space_before_bool) so CJK wraps naturally without spaces."""
    units: List[Any] = []
    n = len(cleaned)
    i = 0
    saw_space = False
    while i < n:
        ch = cleaned[i]
        if ch == " ":
            saw_space = True
            i = i + 1
            continue
        if is_wide_codepoint(ord(ch)):
            units.append((ch, saw_space and len(units) > 0))
            saw_space = False
            i = i + 1
            continue
        start = i
        while i < n and cleaned[i] != " " and not is_wide_codepoint(ord(cleaned[i])):
            i = i + 1
        units.append((cleaned[start:i], saw_space and len(units) > 0))
        saw_space = False
    return units


def wrap_lines(
    text: str,
    max_width_px: float,
    font_px: float,
    bold: bool = False,
    max_lines: Optional[int] = None,
) -> Dict[str, Any]:
    """Wrap text on spaces (and CJK character boundaries) without silent truncation.

    Returns:
        {"lines": List[str], "width": float, "height": float, "fits": bool, "hard_broken": bool}
    """
    cleaned = " ".join(str(text or "").split())
    line_h = round(font_px * 1.28, 2)
    if not cleaned:
        return {"lines": [], "width": 0.0, "height": 0.0, "line_height": line_h, "fits": True, "hard_broken": False}

    if max_width_px <= font_px * 0.9:
        return {
            "lines": [cleaned],
            "width": measure_px(cleaned, font_px, bold),
            "height": line_h,
            "line_height": line_h,
            "fits": False,
            "hard_broken": False,
        }

    units = split_wrap_units(cleaned)
    lines: List[str] = []
    current = ""
    hard_broken = False

    for unit, space_before in units:
        if not current:
            if measure_px(unit, font_px, bold) <= max_width_px:
                current = unit
            else:
                if len(unit) > 1:
                    hard_broken = True
                parts = break_long_token(unit, max_width_px, font_px, bold)
                for p in parts[:-1]:
                    lines.append(p)
                current = parts[-1]
        else:
            sep = " " if space_before else ""
            candidate = current + sep + unit
            if measure_px(candidate, font_px, bold) <= max_width_px:
                current = candidate
            else:
                lines.append(current)
                if measure_px(unit, font_px, bold) <= max_width_px:
                    current = unit
                else:
                    if len(unit) > 1:
                        hard_broken = True
                    parts = break_long_token(unit, max_width_px, font_px, bold)
                    for p in parts[:-1]:
                        lines.append(p)
                    current = parts[-1]

    if current:
        lines.append(current)

    max_w = 0.0
    for ln in lines:
        w = measure_px(ln, font_px, bold)
        if w > max_w:
            max_w = w

    fits = max_w <= (max_width_px + 0.5)
    if max_lines is not None and len(lines) > max_lines:
        fits = False
    # Hard-breaking a normal word inside a narrow box signals poor fit so autofit shrinks font first
    if hard_broken and len(cleaned) <= 28:
        fits = False

    total_h = round(len(lines) * line_h, 2)
    return {
        "lines": lines,
        "width": round(max_w, 2),
        "height": total_h,
        "line_height": line_h,
        "fits": fits,
        "hard_broken": hard_broken,
    }


def format_number(val: float, unit: str = "") -> str:
    """Format a number cleanly without trailing float noise."""
    abs_v = abs(val)
    if abs_v >= 1000000000:
        scaled = val / 1000000000.0
        s = f"{scaled:.1f}B" if abs(scaled - round(scaled)) >= 0.05 else f"{int(round(scaled))}B"
    elif abs_v >= 1000000:
        scaled = val / 1000000.0
        s = f"{scaled:.1f}M" if abs(scaled - round(scaled)) >= 0.05 else f"{int(round(scaled))}M"
    elif abs(val - round(val)) < 1e-6:
        s = f"{int(round(val)):,}"
    elif abs(val * 10 - round(val * 10)) < 1e-5:
        s = f"{val:,.1f}"
    else:
        s = f"{val:,.2f}".rstrip("0").rstrip(".")

    if not unit:
        return s
    u = unit.strip()
    if u in ("%", "$", "€", "£", "¥"):
        return f"{u}{s}" if u != "%" else f"{s}%"
    return f"{s} {u}"


def nice_ticks(min_val: float, max_val: float, target_count: int = 5) -> List[float]:
    """Compute human-friendly axis ticks covering [min_val, max_val]."""
    lo = float(min_val)
    hi = float(max_val)
    if hi < lo:
        lo, hi = hi, lo
    if abs(hi - lo) < 1e-9:
        if abs(hi) < 1e-9:
            return [0.0, 1.0, 2.0, 3.0, 4.0]
        if hi > 0:
            lo = 0.0
        else:
            hi = 0.0

    span = hi - lo
    raw_step = span / max(1, target_count - 1)
    mag = 10.0 ** math.floor(math.log10(raw_step))
    norm = raw_step / mag
    if norm <= 1.0:
        nice_norm = 1.0
    elif norm <= 2.0:
        nice_norm = 2.0
    elif norm <= 2.5:
        nice_norm = 2.5
    elif norm <= 5.0:
        nice_norm = 5.0
    else:
        nice_norm = 10.0
    step = nice_norm * mag

    tick_min = math.floor(lo / step + 1e-9) * step
    tick_max = math.ceil(hi / step - 1e-9) * step

    ticks: List[float] = []
    cur = tick_min
    guard = 0
    while cur <= tick_max + step * 0.001 and guard < 20:
        val = 0.0 if abs(cur) < step * 1e-6 else round(cur, 6)
        ticks.append(val)
        cur = cur + step
        guard = guard + 1
    return ticks

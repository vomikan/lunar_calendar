"""
Lunar Calendar Generator — SVG + PNG, без внешних зависимостей кроме Pillow.

Usage:
    python src/lunar_calendar.py              # текущий месяц
    python src/lunar_calendar.py 2026         # все 12 месяцев года
    python src/lunar_calendar.py 2026 3       # март 2026
    python src/lunar_calendar.py 2026 3 out.png

Конфиг:  assets/config.toml
CSV:     assets/slavic_holidays.csv
Вывод:   output/calendar_YYYY_MM.{svg|png}
"""

import calendar
import math
import sys
import os
from datetime import date, datetime

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


# ─────────────────────────────────────────────
#  КОНФИГ
# ─────────────────────────────────────────────

def load_config(config_path: str) -> dict:
    if not config_path or not os.path.exists(config_path):
        return {}
    if tomllib is None:
        print("⚠️  tomllib не найден, используются значения по умолчанию.")
        return {}
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def cfg(config: dict, *keys, default):
    node = config
    for k in keys:
        if not isinstance(node, dict) or k not in node:
            return default
        node = node[k]
    return node


# ─────────────────────────────────────────────
#  MOON PHASE
# ─────────────────────────────────────────────

def moon_phase(year: int, month: int, day: int) -> float:
    y, m = year, month
    if m < 3:
        y -= 1
        m += 12
    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    jd = (math.floor(365.25 * (y + 4716))
          + math.floor(30.6001 * (m + 1))
          + day + b - 1524.5)
    return ((jd - 2451549.5) % 29.53058770576) / 29.53058770576


def prev_month(year, month):
    return (year - 1, 12) if month == 1 else (year, month - 1)

def next_month(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)

def days_in_month(year, month):
    return calendar.monthrange(year, month)[1]


# ─────────────────────────────────────────────
#  СОБЫТИЯ
# ─────────────────────────────────────────────

def load_events(csv_path: str) -> dict:
    events = {}
    if not csv_path or not os.path.exists(csv_path):
        return events
    with open(csv_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("дата") or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            try:
                d = datetime.strptime(parts[0].strip(), "%Y-%m-%d").date()
                title = parts[1].strip()
                events.setdefault(d, []).append(title)
            except ValueError:
                pass
    return events


# ─────────────────────────────────────────────
#  ПЕРЕНОС ТЕКСТА
# ─────────────────────────────────────────────

def wrap_text(text: str, max_chars: int, max_lines: int) -> list:
    words = text.split()
    lines, current = [], ""
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            if len(lines) == max_lines - 1:
                current = word
                break
            current = word
    if current:
        lines.append(current)
    return lines[:max_lines]


# ─────────────────────────────────────────────
#  SVG MOON ICON
# ─────────────────────────────────────────────

def svg_moon(cx, cy, r, phase, faded=False, moon_cfg=None):
    mc    = moon_cfg or {}
    DARK  = mc.get("dark",  "#A08060")
    LIGHT = mc.get("light", "#F5EDD8")
    RING  = mc.get("ring",  "#8B6A40")
    op    = "0.35" if faded else "1"
    cid   = f"mc_{int(cx*10)}_{int(cy*10)}"

    parts = [
        f'<g opacity="{op}">',
        f'<defs><clipPath id="{cid}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath></defs>',
    ]
    def circ(col):
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col}" clip-path="url(#{cid})"/>'

    p = phase
    if p < 0.03 or p > 0.97:
        parts.append(circ(DARK))
    elif 0.48 < p < 0.52:
        parts.append(circ(LIGHT))
    elif p < 0.5:
        parts.append(circ(DARK))
        parts.append(f'<path d="M {cx} {cy-r} A {r} {r} 0 0 1 {cx} {cy+r} Z" fill="{LIGHT}" clip-path="url(#{cid})"/>')
        t = p / 0.5
        sx = r * abs(math.cos(t * math.pi))
        parts.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{sx:.2f}" ry="{r}" fill="{DARK if t<0.5 else LIGHT}" clip-path="url(#{cid})"/>')
    else:
        parts.append(circ(DARK))
        parts.append(f'<path d="M {cx} {cy-r} A {r} {r} 0 0 0 {cx} {cy+r} Z" fill="{LIGHT}" clip-path="url(#{cid})"/>')
        t = (p - 0.5) / 0.5
        sx = r * abs(math.cos(t * math.pi))
        parts.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{sx:.2f}" ry="{r}" fill="{LIGHT if t<0.5 else DARK}" clip-path="url(#{cid})"/>')

    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{RING}" stroke-width="0.8"/>')
    parts.append('</g>')
    return "\n".join(parts)


# ─────────────────────────────────────────────
#  SVG GENERATOR
# ─────────────────────────────────────────────

MONTH_NAMES_RU = [
    '', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]
DAY_NAMES_RU = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']


def build_weeks(year, month):
    """Возвращает список недель, каждая ячейка = (day, year, month, faded)."""
    cal   = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)
    py, pm = prev_month(year, month)
    ny, nm = next_month(year, month)
    prev_total = days_in_month(py, pm)

    ext = []
    for week in weeks:
        ext.append([(d, year, month, False) if d != 0 else None for d in week])

    first_week = ext[0]
    first_col  = next(i for i, c in enumerate(first_week) if c is not None)
    for col in range(first_col - 1, -1, -1):
        d = prev_total - (first_col - 1 - col)
        first_week[col] = (d, py, pm, True)

    last_week = ext[-1]
    nd = 1
    for col in range(7):
        if last_week[col] is None:
            last_week[col] = (nd, ny, nm, True)
            nd += 1

    return ext


def generate_svg(year: int, month: int, events: dict = None, config: dict = None) -> str:
    if events is None: events = {}
    C = config or {}

    CELL_W   = cfg(C, "layout", "cell_width",    default=120)
    CELL_H   = cfg(C, "layout", "cell_height",   default=90)
    HEADER_H = cfg(C, "layout", "header_height", default=44)
    MOON_R   = cfg(C, "layout", "moon_radius",   default=18)
    CORNER_R = cfg(C, "layout", "corner_radius", default=12)
    PAD      = cfg(C, "layout", "cell_padding",  default=6)
    FADE_OP  = str(cfg(C, "layout", "faded_opacity", default=0.30))

    BG       = cfg(C, "colors", "background", "page",           default="#F7F3EC")
    CELL_WD  = cfg(C, "colors", "background", "cell_weekday",   default="#F0E2B6")
    CELL_WE  = cfg(C, "colors", "background", "cell_weekend",   default="#F2C4A0")
    HDR_WD   = cfg(C, "colors", "background", "header_weekday", default="#E8D89A")
    HDR_WE   = cfg(C, "colors", "background", "header_weekend", default="#EDAA80")
    SHADOW   = cfg(C, "colors", "background", "cell_shadow",    default="rgba(0,0,0,0.07)")

    TXT_MAIN = cfg(C, "colors", "text", "day_number_weekday", default="#5C3D0A")
    TXT_WE   = cfg(C, "colors", "text", "day_number_weekend", default="#7A2E0A")
    TXT_HDR  = cfg(C, "colors", "text", "header_weekday",     default="#6B4A10")
    TXT_HDRW = cfg(C, "colors", "text", "header_weekend",     default="#8B3510")

    moon_cfg = cfg(C, "colors", "moon", default={})

    EVT_TXT   = cfg(C, "colors", "events", "text",       default="#6B2800")
    EVT_FADED = cfg(C, "colors", "events", "text_faded", default="#A07040")

    HDR_SIZE  = cfg(C, "fonts", "header",     "size",           default=14)
    HDR_W     = cfg(C, "fonts", "header",     "weight",         default="bold")
    HDR_LS    = cfg(C, "fonts", "header",     "letter_spacing", default=2)
    FONT_FAM  = cfg(C, "fonts", "header",     "family",         default="Georgia, serif")
    DAY_SIZE  = cfg(C, "fonts", "day_number", "size",           default=24)
    DAY_W     = cfg(C, "fonts", "day_number", "weight",         default="bold")
    EVT_SIZE  = cfg(C, "fonts", "event",      "size",           default=13)
    EVT_LH    = cfg(C, "fonts", "event",      "line_height",    default=14)
    EVT_MC    = cfg(C, "fonts", "event",      "max_chars",      default=13)
    EVT_ML    = cfg(C, "fonts", "event",      "max_lines",      default=3)

    weeks   = build_weeks(year, month)
    NW      = len(weeks)
    total_w = CELL_W * 7 + PAD * 8
    total_h = HEADER_H + CELL_H * NW + PAD * (NW + 2)

    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" '
             f'viewBox="0 0 {total_w} {total_h}" font-family="{FONT_FAM}">')
    L.append(f'<rect width="{total_w}" height="{total_h}" fill="{BG}"/>')

    L.append('<g id="layer-grid">')
    for col, name in enumerate(DAY_NAMES_RU):
        is_we = col >= 5
        x = PAD + col * (CELL_W + PAD)
        L.append(f'<rect x="{x}" y="{PAD}" width="{CELL_W}" height="{HEADER_H-PAD}" '
                 f'rx="{CORNER_R}" fill="{HDR_WE if is_we else HDR_WD}"/>')
        L.append(f'<text x="{x+CELL_W/2}" y="{PAD+(HEADER_H-PAD)/2}" '
                 f'text-anchor="middle" dominant-baseline="middle" '
                 f'font-size="{HDR_SIZE}" font-weight="{HDR_W}" letter-spacing="{HDR_LS}" '
                 f'fill="{TXT_HDRW if is_we else TXT_HDR}">{name}</text>')

    for row, week in enumerate(weeks):
        for col, cell in enumerate(week):
            if cell is None: continue
            day, cy, cm, faded = cell
            is_we = col >= 5
            x = PAD + col * (CELL_W + PAD)
            y = HEADER_H + PAD + row * (CELL_H + PAD)
            bg = CELL_WE if is_we else CELL_WD
            op = FADE_OP if faded else "1"

            L.append(f'<g opacity="{op}">')
            L.append(f'<rect x="{x+1}" y="{y+1}" width="{CELL_W}" height="{CELL_H}" rx="{CORNER_R}" fill="{SHADOW}"/>')
            L.append(f'<rect x="{x}" y="{y}" width="{CELL_W}" height="{CELL_H}" rx="{CORNER_R}" fill="{bg}"/>')
            tc = TXT_WE if is_we else TXT_MAIN
            L.append(f'<text x="{x+10}" y="{y+18}" dominant-baseline="middle" '
                     f'font-size="{DAY_SIZE}" font-weight="{DAY_W}" fill="{tc}">{day}</text>')
            L.append('</g>')

            phase = moon_phase(cy, cm, day)
            mx = x + CELL_W - MOON_R - 8
            my = y + MOON_R + 8
            L.append(svg_moon(mx, my, MOON_R, phase, faded=faded, moon_cfg=moon_cfg))

    L.append('</g>')  # layer-grid

    L.append('<g id="layer-events">')
    for row, week in enumerate(weeks):
        for col, cell in enumerate(week):
            if cell is None: continue
            day, cy, cm, faded = cell
            ev_date = date(cy, cm, day)
            if ev_date not in events: continue

            x = PAD + col * (CELL_W + PAD)
            y = HEADER_H + PAD + row * (CELL_H + PAD)

            all_lines = []
            for title in events[ev_date]:
                slots = EVT_ML - len(all_lines)
                if slots <= 0: break
                all_lines.extend(wrap_text(title, EVT_MC, slots))
            all_lines = all_lines[:EVT_ML]

            tc   = EVT_FADED if faded else EVT_TXT
            t_op = "0.5" if faded else "1"
            ty0  = y + CELL_H - len(all_lines) * EVT_LH - 6

            L.append(f'<g opacity="{t_op}">')
            for i, line in enumerate(all_lines):
                L.append(f'<text x="{x+8}" y="{ty0 + i*EVT_LH}" dominant-baseline="middle" '
                         f'font-size="{EVT_SIZE}" font-weight="bold" fill="{tc}">{line}</text>')
            L.append('</g>')

    L.append('</g>')  # layer-events
    L.append('</svg>')
    return "\n".join(L)



# ─────────────────────────────────────────────
#  SAVE
# ─────────────────────────────────────────────

def save_calendar(year: int, month: int, out_path: str,
                  events: dict, config: dict):
    """Генерирует и сохраняет SVG одного месяца."""
    svg = generate_svg(year, month, events, config)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    evt_count = sum(1 for d in events if d.year == year and d.month == month)
    print(f"  ✅  {MONTH_NAMES_RU[month]:10s} {year}  →  {out_path}  ({evt_count} событий)")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def find_asset(filename: str, script_path: str) -> str | None:
    script_dir = os.path.dirname(os.path.abspath(script_path))
    for c in [
        os.path.join(script_dir, "..", "assets", filename),
        os.path.join("assets", filename),
    ]:
        if os.path.exists(c):
            return os.path.normpath(c)
    return None


def main():
    today = date.today()
    args  = sys.argv[1:]

    year = month = out = None

    if len(args) == 0:
        year, month = today.year, today.month
    elif len(args) == 1 and len(args[0]) == 4 and args[0].isdigit():
        year = int(args[0])   # весь год
    elif len(args) >= 2:
        year, month = int(args[0]), int(args[1])
        if len(args) == 3:
            out = args[2]
    else:
        print(__doc__)
        sys.exit(1)

    config_path = find_asset("config.toml",         sys.argv[0])
    csv_path    = find_asset("slavic_holidays.csv", sys.argv[0])
    config      = load_config(config_path)
    events      = load_events(csv_path)

    out_dir = cfg(config, "output", "directory", default="output")
    os.makedirs(out_dir, exist_ok=True)

    print(f"📅  Генерация  |  конфиг: {config_path or '—'}  |  csv: {csv_path or '—'}")

    if month is None:
        print(f"    Год {year}, все 12 месяцев → {out_dir}/\n")
        for m in range(1, 13):
            path = os.path.join(out_dir, f"calendar_{year}_{m:02d}.svg")
            save_calendar(year, m, path, events, config)
    else:
        if out is None:
            out = os.path.join(out_dir, f"calendar_{year}_{month:02d}.svg")
        save_calendar(year, month, out, events, config)

    print(f"\n✨  Готово.")


if __name__ == "__main__":
    main()

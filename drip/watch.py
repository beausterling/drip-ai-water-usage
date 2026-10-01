"""`drip watch` — live water meter for a terminal split pane.

Works in any terminal (Ghostty, Warp, iTerm2, Terminal, ...). Adapts to the pane:
  1–3 rows  -> a one-line status bar (put it in a thin strip under Codex/Gemini)
  taller    -> a panel with a filling bottle, totals and a per-minute sparkline
"""
import os
import shutil
import signal
import sys
import time
from datetime import date, datetime, timedelta, timezone

from . import ledger
from .coeffs import Coefficients, Tokens, fmt_ml, relatable

WATER, DEEP, FOAM, DIM, BOLD, RESET = ("\x1b[38;5;39m", "\x1b[38;5;25m", "\x1b[38;5;117m",
                                       "\x1b[2m", "\x1b[1m", "\x1b[0m")
SPARK = " ▁▂▃▄▅▆▇█"
BOTTLE_ML = 500  # the mini bottle fills once per 500 mL bottle
TOKEN_COLS = "input, output, cache_read, cache_write"


def snapshot(db, coeffs, tool=None, band="mid", onsite=False, minutes=30):
    """Active session (most recent activity), its water, today's water, per-minute series."""
    where, args = ("WHERE tool=?", (tool,)) if tool else ("", ())
    row = db.execute(f"SELECT session, tool, project, model FROM usage {where} ORDER BY ts DESC LIMIT 1", args).fetchone()
    if not row:
        return None
    session, tool_name, project, model = row
    s_ml = 0.0
    since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    series = [0.0] * minutes
    now = datetime.now(timezone.utc)
    for m, ts, *tk in db.execute(f"SELECT model, ts, {TOKEN_COLS} FROM usage WHERE session=?", (session,)):
        ml = coeffs.water_ml(Tokens(*tk), m, band, onsite)
        s_ml += ml
        if ts and ts >= since[:19]:
            try:
                age = (now - datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 60
                series[max(0, minutes - 1 - int(age))] += ml
            except ValueError:
                pass
    today = sum(coeffs.water_ml(Tokens(*tk), m, band, onsite) for m, *tk in db.execute(
        f"SELECT model, SUM(input), SUM(output), SUM(cache_read), SUM(cache_write) FROM usage "
        f"WHERE day=? GROUP BY model", (date.today().isoformat(),)))
    return {"session": session, "tool": tool_name, "project": os.path.basename(project or ""),
            "model": model, "ml": s_ml, "today": today, "series": series,
            "rate": sum(series[-5:]) / 5}


def spark(vals, width):
    vals = vals[-width:]
    mx = max(vals) or 1
    return "".join(SPARK[min(8, round(v / mx * 8))] if v else "·" for v in vals)


def line_view(s, cols):
    """One-line status bar; drops fields right-to-left until it fits."""
    parts = [f"{WATER}💧 {fmt_ml(s['ml'])}{RESET} session",
             f"{BOLD}{fmt_ml(s['today'])}{RESET} today",
             f"{FOAM}{spark(s['series'], 12)}{RESET} {fmt_ml(s['rate'])}/min",
             f"{DIM}{s['model']}{RESET}",
             f"{DIM}{relatable(s['ml'])}{RESET}"]
    import re
    vis = lambda t: len(re.sub(r"\x1b\[[0-9;]*m", "", t)) + t.count("💧")
    while len(parts) > 1 and vis(" · ".join(parts)) > cols - 1:
        parts.pop()
    return " · ".join(parts)


def bottle(fill, t):
    """8-row bottle; fill in [0,1]."""
    shape = ["  .---.  ", "  |___|  ", "  |   |  ", " /     \\ ", "|       |", "|       |", "|       |", "|       |", " \\_____/ "]
    rows = len(shape) - 4  # fillable body rows (indices 3..7)
    level = fill * (rows + 0.999)
    out = []
    for i, r in enumerate(shape):
        body = 3 <= i <= 7
        from_bottom = 7 - i
        if body and from_bottom < level:
            a, b = r.index("|" if i > 3 else "/") + 1, r.rindex("|" if i > 3 else "\\")
            top = from_bottom >= int(level) - 0 and from_bottom == int(level)
            ch = ("≈" if (t + i) % 2 else "~") if top else ("▓" if from_bottom < 2 else "▒")
            col = FOAM if top else (DEEP if from_bottom < 2 else WATER)
            out.append(DIM + r[:a] + RESET + col + ch * (b - a) + RESET + DIM + r[b:] + RESET)
        else:
            out.append(DIM + r + RESET)
    return out


def panel_view(s, cols, rows, t):
    bottles = s["ml"] / BOTTLE_ML
    b = bottle(bottles - int(bottles) if s["ml"] else 0, t)
    info = [
        f"{BOLD}{WATER}💧 drip{RESET}  {DIM}{s['tool']} · {s['project']}{RESET}",
        "",
        f"{DIM}session{RESET}  {WATER}{BOLD}{fmt_ml(s['ml'])}{RESET}",
        f"{DIM}         {relatable(s['ml'])}{RESET}",
        f"{DIM}today  {RESET}  {BOLD}{fmt_ml(s['today'])}{RESET}",
        f"{DIM}rate   {RESET}  {fmt_ml(s['rate'])}/min",
        f"{DIM}model  {RESET}  {s['model']}",
        f"{DIM}bottles{RESET}  {int(bottles)} × 500 mL" + (" filled" if bottles >= 1 else ""),
        "",
    ]
    w = max(8, cols - 4)
    lines = []
    if cols >= 44:
        for i in range(max(len(b), len(info))):
            left = b[i] if i < len(b) else " " * 9
            lines.append(" " + left + "   " + (info[i] if i < len(info) else ""))
    else:
        lines = [" " + x for x in info]
    lines += ["", f" {DIM}last 30 min{RESET}", " " + FOAM + spark(s["series"], min(30, w)) + RESET,
              "", f" {DIM}ctrl+c to quit · drip open for full breakdown{RESET}"]
    return lines[:rows]


def run(tool=None, band="mid", onsite=False, interval=2.0, until_pid=None):
    coeffs = Coefficients()
    db = ledger.connect()
    out = sys.stdout
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    out.write("\x1b[?1049h\x1b[?25l")  # alt screen, hide cursor
    t = 0
    last_sync = 0.0
    try:
        while not stop:
            if until_pid:
                try:
                    os.kill(until_pid, 0)
                except ProcessLookupError:
                    break  # the agent exited; close the meter pane with it
                except PermissionError:
                    pass
            if time.time() - last_sync > interval:
                ledger.sync(db)
                last_sync = time.time()
            cols, rows = shutil.get_terminal_size((80, 24))
            s = snapshot(db, coeffs, tool, band, onsite)
            if not s:
                frame = [f"{DIM}💧 waiting for agent activity…{RESET}"]
            elif rows <= 3:
                frame = [line_view(s, cols)]
            else:
                frame = panel_view(s, cols, rows, t)
            out.write("\x1b[H\x1b[2J" + "\r\n".join(frame))
            out.flush()
            t += 1
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        out.write("\x1b[?25h\x1b[?1049l")
        out.flush()

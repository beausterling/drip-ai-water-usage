"""drip — estimated water used by terminal AI agents.

  drip statusline            status-line segment (reads Claude Code's JSON on stdin)
  drip session [ID]          breakdown for one session (default: most recent)
  drip history [--by day|week|month|model|tool|project] [--days N]
  drip sync                  import new transcript data (Claude Code + Codex)
  drip explain [MODEL]       show the coefficients and math
  drip install               first-time setup (animated), wires the Claude Code status line
  drip splash                replay the intro animation
  drip open                  open the detailed breakdown in your browser
  drip watch [--tool codex]  live meter for a split pane (1-line bar when the pane is short)
  drip run codex             run an agent with the meter opened beside it (Ghostty, Warp, iTerm2, tmux, Terminal)

Global flags: --band low|mid|high (default mid), --onsite (cooling water only)
"""
import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import date, timedelta

from . import ledger
from .coeffs import BANDS, Coefficients, Tokens, fmt_ml, relatable

SYNC_EVERY_S = 60
_TTY = sys.stdout.isatty()
CYAN, RESET = ("\x1b[36m", "\x1b[0m") if _TTY else ("", "")


def rows_to_totals(rows, coeffs, band, onsite):
    """rows: (group, model, in, out, cr, cw) -> {group: [ml, wh, Tokens, estimated]}"""
    out = defaultdict(lambda: [0.0, 0.0, Tokens(), False])
    for group, model, *tk in rows:
        t = Tokens(*tk)
        acc = out[group]
        acc[0] += coeffs.water_ml(t, model, band, onsite)
        acc[1] += coeffs.energy_wh(t, model, band)
        acc[2] += t
        acc[3] = acc[3] or coeffs.is_estimated(model)
    return out


TOKEN_COLS = "SUM(input), SUM(output), SUM(cache_read), SUM(cache_write)"


def session_total(db, coeffs, session, band, onsite):
    rows = db.execute(f"SELECT '', model, {TOKEN_COLS} FROM usage WHERE session=? GROUP BY model", (session,)).fetchall()
    return rows_to_totals(rows, coeffs, band, onsite).get("", [0.0, 0.0, Tokens(), False])


def day_total(db, coeffs, day, band, onsite):
    rows = db.execute(f"SELECT '', model, {TOKEN_COLS} FROM usage WHERE day=? GROUP BY model", (day,)).fetchall()
    return rows_to_totals(rows, coeffs, band, onsite).get("", [0.0, 0.0, Tokens(), False])


def background_sync(db):
    """Kick off a full sync in a detached process if the last one is stale."""
    row = db.execute("SELECT v FROM meta WHERE k='last_sync'").fetchone()
    lock = os.path.join(os.path.dirname(ledger.DB_PATH), "sync.lock")
    try:
        if os.path.exists(lock) and time.time() - os.path.getmtime(lock) < 600:
            return
        if row and time.time() - time.mktime(time.strptime(row[0][:19], "%Y-%m-%dT%H:%M:%S")) < SYNC_EVERY_S:
            return
        open(lock, "w").close()
        pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.Popen(
            [sys.executable, "-c", f"import sys,os;sys.path.insert(0,{pkg_parent!r});"
             "from drip import ledger;db=ledger.connect();ledger.sync(db);"
             f"os.remove({lock!r})"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
    except Exception:
        pass


def statusline_segment(payload, band="mid", onsite=False, color=True):
    coeffs = Coefficients()
    db = ledger.connect()
    tp = payload.get("transcript_path")
    session = payload.get("session_id")
    if tp:
        ledger.sync(db, ledger.claude_session_files(tp))
        session = session or os.path.splitext(os.path.basename(tp))[0]
    background_sync(db)
    ml, _, _, est = session_total(db, coeffs, session, band, onsite)
    today_ml = day_total(db, coeffs, date.today().isoformat(), band, onsite)[0]
    approx = "~" if est else ""
    seg = f"💧 {approx}{fmt_ml(ml)} ({relatable(ml)})"
    if abs(today_ml - ml) > ml * 0.01:
        seg += f" · today {fmt_ml(today_ml)}"
    seg = f"\x1b[36m{seg}\x1b[0m" if color else seg
    if os.environ.get("DRIP_LINKS", "1") != "0":
        seg = hyperlink(seg, refresh_report(db, band, onsite), session)
    return seg


REPORT_EVERY_S = 15


def refresh_report(db, band, onsite):
    """Rewrite the HTML breakdown at most every REPORT_EVERY_S seconds."""
    from . import report
    try:
        if time.time() - os.path.getmtime(report.REPORT_PATH) < REPORT_EVERY_S:
            return report.REPORT_PATH
    except OSError:
        pass
    try:
        report.write(db, band, onsite)
    except Exception:
        pass
    return report.REPORT_PATH


def hyperlink(text, path, session=None):
    """OSC 8 link (Cmd/Ctrl+click in iTerm2, Ghostty, WezTerm, Kitty, ...).
    Terminals without OSC 8 support ignore the escape and show plain text."""
    url = "file://" + path + (f"#{session}" if session else "")
    return f"\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\"


# ---------------------------- commands ----------------------------

def cmd_statusline(a):
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        sys.stdout.write(statusline_segment(payload, a.band, a.onsite))
    except Exception:
        pass
    return 0


def cmd_sync(a):
    t = time.time()
    n = ledger.sync(ledger.connect())
    print(f"imported {n} new responses in {time.time() - t:.1f}s")


def fmt_tokens(n):
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.0f}K" if n >= 1e3 else str(n)


def cmd_session(a):
    coeffs, db = Coefficients(), ledger.connect()
    ledger.sync(db)
    sid = a.id or (db.execute("SELECT session FROM usage ORDER BY ts DESC LIMIT 1").fetchone() or [None])[0]
    if not sid:
        return print("no sessions found")
    rows = db.execute(f"SELECT model, model, {TOKEN_COLS} FROM usage WHERE session LIKE ? GROUP BY model", (sid + "%",)).fetchall()
    meta = db.execute("SELECT tool, project, MIN(ts), MAX(ts) FROM usage WHERE session LIKE ?", (sid + "%",)).fetchone()
    print(f"session {sid}  ({meta[0]}, {meta[1]})\n{meta[2]} → {meta[3]}\n")
    totals = rows_to_totals(rows, coeffs, a.band, a.onsite)
    w = max([22] + [len(m) + 3 for m in totals])
    print(f"{'model':<{w}}{'input':>9}{'output':>9}{'c.read':>9}{'c.write':>9}{'energy':>10}{'water':>10}")
    sum_ml = 0
    for model, (ml, wh, t, est) in sorted(totals.items(), key=lambda kv: -kv[1][0]):
        sum_ml += ml
        print(f"{model + ('~' if est else ''):<{w}}{fmt_tokens(t.input):>9}{fmt_tokens(t.output):>9}"
              f"{fmt_tokens(t.cache_read):>9}{fmt_tokens(t.cache_write):>9}{wh:>8.1f}Wh{fmt_ml(ml):>10}")
    print(f"\ntotal: {fmt_ml(sum_ml)} ≈ {relatable(sum_ml)}   [{a.band}{', on-site only' if a.onsite else ''}]")
    bands = "  ".join(f"{b}: {fmt_ml(sum(coeffs.water_ml(Tokens(*r[2:]), r[1], b, a.onsite) for r in rows))}" for b in BANDS)
    print(f"range  {bands}")


def spark(vals):
    bars = "▁▂▃▄▅▆▇█"
    m = max(vals) or 1
    return "".join(bars[min(7, int(v / m * 7.999))] if v else " " for v in vals)


def cmd_history(a):
    coeffs, db = Coefficients(), ledger.connect()
    ledger.sync(db)
    since = (date.today() - timedelta(days=a.days - 1)).isoformat() if a.days else "0000"
    group = {
        "day": "day",
        "week": "strftime('%Y-W%W', day)",
        "month": "substr(day, 1, 7)",
        "model": "model",
        "tool": "tool",
        "project": "project",
    }[a.by]
    rows = db.execute(
        f"SELECT {group}, model, {TOKEN_COLS} FROM usage WHERE day >= ? GROUP BY 1, 2", (since,)).fetchall()
    totals = rows_to_totals(rows, coeffs, a.band, a.onsite)
    if not totals:
        return print("no usage recorded yet — try `drip sync`")
    items = sorted(totals.items(), key=lambda kv: str(kv[0])) if a.by in ("day", "week", "month") \
        else sorted(totals.items(), key=lambda kv: -kv[1][0])
    width = max(len(str(k)) for k, _ in items) + 2
    peak = max(v[0] for _, v in items) or 1
    for key, (ml, wh, t, est) in items:
        bar = "█" * max(1, round(ml / peak * 30)) if ml else ""
        label = str(key or "?") + ("~" if est else "")
        print(f"{label:<{width}}{fmt_ml(ml):>9}  {wh / 1000:>7.2f} kWh  {fmt_tokens(t.total):>8} tok  {CYAN}{bar}{RESET}")
    total = sum(v[0] for _, v in items)
    print(f"\ntotal {fmt_ml(total)} ≈ {relatable(total)}   [{a.band}{', on-site only' if a.onsite else ''}]")
    if a.by == "day" and len(items) > 1:
        print("trend", spark([v[0] for _, v in items]))


def cmd_explain(a):
    c = Coefficients()
    print(f"coefficients: {c.path} (reviewed {c.cfg.get('last_reviewed')})\n")
    print("water (mL) = Wh × water factor (L/kWh)")
    for b in BANDS:
        print(f"  {b:<5} water factor {c.water_factor(b):.2f} L/kWh   on-site only {c.water_factor(b, True):.3f}")
    models = [a.model] if a.model else [m["match"].rstrip("*") for m in c.cfg["model"] if not m.get("fallback")]
    print(f"\nmL per 1K tokens [{a.band}{', on-site' if a.onsite else ''}]")
    print(f"{'model':<20}{'input':>9}{'output':>9}{'c.read':>9}{'c.write':>9}")
    wf = c.water_factor(a.band, a.onsite)
    for m in models:
        k = c.per_1k_wh(m, a.band)
        print(f"{m:<20}" + "".join(f"{k[x] * wf:>9.3f}" for x in ("input", "output", "cache_read", "cache_write")))
    print("\nPer-model scaling uses list price (the only public signal). Inference only; training excluded.")
    print("Derivation and sources: RESEARCH.md; prices: PRICING.md")


INSTALLED_MARKER = os.path.join(os.path.dirname(ledger.DB_PATH), "installed")
SETTINGS = os.path.expanduser("~/.claude/settings.json")


def wire_statusline():
    """Point Claude Code's status line at drip, without clobbering a custom one."""
    try:
        with open(SETTINGS) as f:
            settings = json.load(f)
    except (OSError, ValueError):
        settings = {}
    cur = (settings.get("statusLine") or {}).get("command", "")
    script = os.path.expanduser(cur.split()[-1]) if cur else ""
    already = "drip" in cur or (os.path.isfile(script) and "drip" in open(script, errors="ignore").read())
    if already:
        return "status line: already showing water ✓"
    if cur:
        return ("status line: you have a custom one — add this segment to it:\n"
                "    from drip.cli import statusline_segment; parts.append(statusline_segment(data))\n"
                "  or append the output of:  echo \"$input\" | drip statusline")
    drip = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "drip")
    settings["statusLine"] = {"type": "command", "command": f"{drip} statusline", "padding": 0}
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    with open(SETTINGS, "w") as f:
        json.dump(settings, f, indent=2)
    return "status line: enabled ✓ (restart Claude Code to see it)"


def link_on_path():
    """Put `drip` on PATH via ~/.local/bin (created if needed)."""
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "drip")
    bindir = os.path.expanduser("~/.local/bin")
    dst = os.path.join(bindir, "drip")
    try:
        os.makedirs(bindir, exist_ok=True)
        if os.path.realpath(dst) != os.path.realpath(src):
            if os.path.lexists(dst):
                return f"command: {dst} already exists — not overwriting"
            os.symlink(src, dst)
    except OSError as e:
        return f"command: couldn't link {dst} ({e})"
    on_path = bindir in os.environ.get("PATH", "").split(os.pathsep)
    return "command: `drip` is on your PATH ✓" if on_path else \
        f'command: linked {dst} — add it to PATH:  echo \'export PATH="$HOME/.local/bin:$PATH"\' >> ~/.zshrc'


def cmd_install(a):
    import threading
    from . import splash
    result = {}

    def work():
        db = ledger.connect()
        result["n"] = ledger.sync(db)
        rows = db.execute(f"SELECT '', model, {TOKEN_COLS} FROM usage GROUP BY model").fetchall()
        result["ml"] = rows_to_totals(rows, Coefficients(), a.band, a.onsite).get("", [0])[0]
        result["sessions"] = db.execute("SELECT COUNT(DISTINCT session) FROM usage").fetchone()[0]

    th = threading.Thread(target=work)
    th.start()
    th.join(timeout=0.3)
    msg = [f"{splash.DIM}a water meter for terminal AI agents{splash.RESET}"]
    if not th.is_alive():
        msg += ["", f"{splash.WATER}{fmt_ml(result['ml'])}{splash.RESET} across {result['sessions']} sessions so far",
                f"{splash.DIM}≈ {relatable(result['ml'])}{splash.RESET}"]
    if not sys.stdout.isatty() and splash.play_in_new_window():
        print("💧 playing the intro in a new terminal window")
    else:
        splash.play(msg)
    th.join()
    if "ml" in result and len(msg) == 1:
        print(f"  {fmt_ml(result['ml'])} across {result['sessions']} sessions so far ≈ {relatable(result['ml'])}")
    print()
    print("  " + link_on_path())
    print("  " + wire_statusline())
    print("  try:  drip · drip session · drip history --by model · drip explain\n")
    os.makedirs(os.path.dirname(INSTALLED_MARKER), exist_ok=True)
    open(INSTALLED_MARKER, "w").close()


def cmd_open(a):
    from . import report
    db = ledger.connect()
    ledger.sync(db)
    path = report.write(db, a.band, a.onsite)
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        subprocess.run([opener, path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"opened {path}")
    except FileNotFoundError:
        print(f"breakdown written to {path}")


def cmd_overview(a):
    """Bare `drip`: this session, today, and the last 14 days."""
    cmd_session(a)
    print()
    a.by, a.days = "day", 14
    cmd_history(a)
    print("\nmore: drip open (browser breakdown) · drip history --by model · drip explain")


def cmd_watch(a):
    from . import watch
    watch.run(tool=a.tool, band=a.band, onsite=a.onsite, until_pid=a.until_pid)


def cmd_run(a):
    from . import run
    return run.main(a.argv, layout=a.layout)


def cmd_splash(a):
    from . import splash
    if not sys.stdout.isatty() and splash.play_in_new_window():
        return print("💧 playing the intro in a new terminal window")
    db = ledger.connect()
    rows = db.execute(f"SELECT '', model, {TOKEN_COLS} FROM usage GROUP BY model").fetchall()
    ml = rows_to_totals(rows, Coefficients(), a.band, a.onsite).get("", [0])[0]
    n = db.execute("SELECT COUNT(DISTINCT session) FROM usage").fetchone()[0]
    msg = [f"{splash.DIM}a water meter for terminal AI agents{splash.RESET}"]
    if n:
        msg += ["", f"{splash.WATER}{fmt_ml(ml)}{splash.RESET} across {n} sessions so far",
                f"{splash.DIM}≈ {relatable(ml)}{splash.RESET}"]
    splash.play(msg)


def main(argv=None):
    p = argparse.ArgumentParser(prog="drip", description="Estimated water used by terminal AI agents.")
    p.add_argument("--band", choices=BANDS, default=os.environ.get("DRIP_BAND", "mid"))
    p.add_argument("--onsite", action="store_true", default=os.environ.get("DRIP_ONSITE") == "1",
                   help="count only data-center cooling water (Google/OpenAI boundary)")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("statusline").set_defaults(fn=cmd_statusline)
    sub.add_parser("sync").set_defaults(fn=cmd_sync)
    s = sub.add_parser("session")
    s.add_argument("id", nargs="?")
    s.set_defaults(fn=cmd_session)
    h = sub.add_parser("history")
    h.add_argument("--by", choices=["day", "week", "month", "model", "tool", "project"], default="day")
    h.add_argument("--days", type=int, default=None)
    h.set_defaults(fn=cmd_history)
    e = sub.add_parser("explain")
    e.add_argument("model", nargs="?")
    e.set_defaults(fn=cmd_explain)
    sub.add_parser("install").set_defaults(fn=cmd_install)
    sub.add_parser("splash").set_defaults(fn=cmd_splash)
    sub.add_parser("open").set_defaults(fn=cmd_open)
    w = sub.add_parser("watch", help="live meter for a split pane")
    w.add_argument("--tool", choices=["claude-code", "codex"], default=None)
    w.add_argument("--until-pid", type=int, default=None, help=argparse.SUPPRESS)
    w.set_defaults(fn=cmd_watch)
    r = sub.add_parser("run", help="run an agent CLI with the live meter beside it")
    r.add_argument("--layout", choices=["side", "strip"], default=os.environ.get("DRIP_LAYOUT", "side"),
                   help="side: panel with the bottle (default) · strip: one-line bar underneath")
    r.add_argument("argv", nargs=argparse.REMAINDER)
    r.set_defaults(fn=cmd_run)
    a = p.parse_args(argv)
    if not getattr(a, "fn", None):
        # first interactive bare `drip` gets the welcome; subcommands stay read-only
        if not os.path.exists(INSTALLED_MARKER) and sys.stdout.isatty():
            return cmd_install(a)
        a.id = None
        return cmd_overview(a)
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())

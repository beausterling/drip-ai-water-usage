"""Animated water-bottle splash, shown on first install (and by `drip splash`)."""
import math
import random
import shutil
import sys
import time

# Bottle outline. Interior = the columns strictly between the first and last
# non-space character of each row; rows marked False are never filled.
BOTTLE = [
    ("    |     |    ", True),   # neck
    ("    |     |    ", True),
    ("  .'       '.  ", True),   # shoulders
    (" /           \\ ", True),
    ("|             |", True),
    ("|             |", True),
    ("|             |", True),
    ("|             |", True),
    ("|             |", True),
    ("|             |", True),
    ("|             |", True),
    (" \\___________/ ", False),  # base
]
CAP = ["   .-------.   ", "   |_______|   "]
WIDTH = len(BOTTLE[0][0])
SKY = 4  # empty rows above the bottle for falling drops

TITLE = [
    "     _      _       ",
    "  __| |_ __(_)_ __  ",
    " / _` | '__| | '_ \\ ",
    "| (_| | |  | | |_) |",
    " \\__,_|_|  |_| .__/ ",
    "             |_|    ",
]

GLASS = "\x1b[38;5;252m"
WATER = "\x1b[38;5;33m"
DEEP = "\x1b[38;5;25m"
FOAM = "\x1b[38;5;117m"
BUBBLE = "\x1b[38;5;159m"
TITLE_C = "\x1b[1;38;5;45m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"


def interior(row):
    """[start, end) of the gap between the left and right wall runs."""
    s = row.rstrip()
    lo = len(s) - len(s.lstrip())
    while lo < len(s) and s[lo] != " ":
        lo += 1
    hi = len(s)
    while hi > lo and s[hi - 1] != " ":
        hi -= 1
    return lo, hi


FILLABLE = [i for i, (_, ok) in enumerate(BOTTLE) if ok]
FULL_LEVEL = len(FILLABLE) - 2  # stop just below the neck so it reads as a bottle


def render(level, t, drops, bubbles, cap_y, title_chars, info):
    """level: rows of water from the bottom (float). Returns list of lines."""
    lines = []
    # sky rows (drops + falling cap)
    for y in range(SKY):
        row = [" "] * WIDTH
        for dy, dx in drops:
            if int(dy) == y:
                row[dx] = f"{WATER}●{RESET}"
        lines.append("".join(row))
    # cap (animated drop-in)
    if cap_y is not None:
        for k, c in enumerate(CAP):
            yy = int(cap_y) + k
            if 0 <= yy < SKY:
                lines[yy] = GLASS + c + RESET
    top_row = len(FILLABLE) - level  # index into FILLABLE of the water surface (fractional)
    for i, (shape, ok) in enumerate(BOTTLE):
        chars = [GLASS + ch + RESET if ch != " " else " " for ch in shape]
        if ok:
            a, b = interior(shape)
            fi = FILLABLE.index(i)
            # drops falling inside the bottle
            for dy, dx in drops:
                if int(dy) == SKY + i and a <= dx < b:
                    chars[dx] = f"{WATER}●{RESET}"
            if fi >= math.floor(top_row):
                surface = fi == math.floor(top_row)
                for x in range(a, b):
                    if surface:
                        phase = math.sin(x * 0.9 + t * 7)
                        ch = "≈" if phase > 0.3 else "~" if phase > -0.4 else "-"
                        chars[x] = FOAM + ch + RESET
                    else:
                        depth = fi - top_row
                        ch = "▓" if depth > 4 else "▒"
                        chars[x] = (DEEP if depth > 4 else WATER) + ch + RESET
                for bx, by in bubbles:
                    if int(by) == i and a <= bx < b and fi > math.floor(top_row):
                        chars[bx] = BUBBLE + random.choice("o°∘") + RESET
        lines.append("".join(chars))
    # title + info to the right of the bottle
    out = []
    title_top = SKY + 1
    for n, line in enumerate(lines):
        right = ""
        k = n - title_top
        if 0 <= k < len(TITLE):
            right = TITLE_C + TITLE[k][:title_chars] + RESET
        elif 0 <= k - len(TITLE) - 1 < len(info):
            right = info[k - len(TITLE) - 1]
        out.append("  " + line + "    " + right)
    return out


def play(info=None, duration=3.2, fps=24, out=sys.stdout):
    info = info or []
    if not out.isatty() or shutil.get_terminal_size().columns < 60:
        return static(info, out)
    random.seed(7)
    height = SKY + len(BOTTLE)
    frames = int(duration * fps)
    drops = []
    bubbles = []
    out.write("\x1b[?25l" + "\n" * height)
    try:
        for f in range(frames + 1):
            t = f / fps
            p = f / frames
            # phase 1 (0-35%): drops fall; phase 2 (15-80%): fill; phase 3 (70%+): cap + title
            if p < 0.55 and f % 3 == 0:
                drops.append([0.0, WIDTH // 2 + random.choice((-1, 0, 0, 1))])
            for d in drops:
                d[0] += 1.1
            drops = [d for d in drops if d[0] < SKY + len(BOTTLE) - 2]
            fill = min(1.0, max(0.0, (p - 0.12) / 0.62))
            level = FULL_LEVEL * (1 - (1 - fill) ** 2)  # ease-out
            top = len(FILLABLE) - level
            drops = [d for d in drops if d[0] - SKY < FILLABLE[min(len(FILLABLE) - 1, max(0, math.floor(top)))]]
            if level > 2 and random.random() < 0.5:
                bubbles.append([random.randint(2, WIDTH - 3), float(len(BOTTLE) - 2)])
            for b in bubbles:
                b[1] -= 0.6
            bubbles = [b for b in bubbles if b[1] > FILLABLE[min(len(FILLABLE) - 1, math.floor(top))]]
            cap_y = None
            if p > 0.72:
                cap_y = min(SKY - 2, -2 + (p - 0.72) / 0.12 * SKY)
            title_chars = int(max(0, (p - 0.78) / 0.18) * len(TITLE[0]))
            shown_info = info if p >= 0.97 else []
            frame = render(level, t, drops, bubbles, cap_y, title_chars, shown_info)
            out.write(f"\x1b[{height}A" + "".join("\r\x1b[2K" + l + "\n" for l in frame))
            out.flush()
            time.sleep(1 / fps)
    except KeyboardInterrupt:
        pass
    finally:
        out.write("\x1b[?25h" + RESET)
        out.flush()


def static(info, out=sys.stdout):
    frame = render(FULL_LEVEL, 0, [], [], SKY - 2, len(TITLE[0]), info)
    import re
    strip = (lambda s: re.sub(r"\x1b\[[0-9;]*m", "", s)) if not out.isatty() else (lambda s: s)
    out.write("\n".join(strip(l).rstrip() for l in frame) + "\n")


def play_in_new_window(args=("splash",)):
    """Claude Code (and other non-TTY hosts) can't show live output, so open a real
    terminal window to play the animation. Returns True if a window was launched."""
    import os
    import subprocess
    import tempfile
    if sys.platform != "darwin":
        return False
    drip = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "drip")
    script = tempfile.NamedTemporaryFile("w", suffix=".command", delete=False, prefix="drip-")
    script.write(f"#!/bin/zsh\nclear\n'{drip}' {' '.join(args)}\n"
                 "printf '\\n  \\e[2mpress any key to close\\e[0m'; read -s -k 1\n"
                 f"rm -f '{script.name}'\nexit\n")
    script.close()
    os.chmod(script.name, 0o755)
    term = os.environ.get("TERM_PROGRAM", "")
    app = {"iTerm.app": "iTerm", "ghostty": "Ghostty", "WarpTerminal": "Warp", "WezTerm": "WezTerm"}.get(term, "Terminal")
    for candidate in (app, "Terminal"):
        if subprocess.run(["open", "-a", candidate, script.name], stderr=subprocess.DEVNULL).returncode == 0:
            return True
    return False


if __name__ == "__main__":
    play([f"{DIM}water meter for terminal AI agents{RESET}"])

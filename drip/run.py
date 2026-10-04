"""`drip run <cmd>` — run an agent CLI with a live water meter beside it.

Picks the best layout the current terminal can script:
  tmux (inside or installed)  split pane beside (or under) the agent
  Ghostty 1.3+ / iTerm2       AppleScript split of the current tab
  Warp                        new tab from a Tab Config: agent + meter side by side
  Terminal.app / other        small separate meter window, or just a tip
Layouts: "side" (default) is a ~40-column panel with the animated bottle;
"strip" is a 3-row one-line bar under the agent.
The meter pane exits by itself when the agent exits (--until-pid).
"""
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

TOOL_FOR = {"codex": "codex", "claude": "claude-code"}

# Agents that are often installed inside an app bundle rather than on PATH.
KNOWN_LOCATIONS = {
    "codex": ["/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex",
              "/Applications/Codex.app/Contents/Resources/codex",
              "~/.codex/bin/codex", "/opt/homebrew/bin/codex", "/usr/local/bin/codex"],
    "claude": ["~/.claude/local/claude", "~/.local/bin/claude", "/opt/homebrew/bin/claude"],
    "gemini": ["/opt/homebrew/bin/gemini", "/usr/local/bin/gemini"],
}


def resolve(cmd):
    """Path to cmd: PATH first, then known install locations."""
    found = shutil.which(cmd)
    if found:
        return found
    for p in KNOWN_LOCATIONS.get(cmd, []):
        p = os.path.expanduser(p)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def drip_bin():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "drip")


SIDE_COLS = 40   # side panel: room for the bottle + totals
STRIP_ROWS = 3   # strip: one-line bar


def watch_cmd(argv, pid=None, pidfile=None):
    """Shell command for the meter pane. Uses this exact Python (panes opened by
    a terminal often get a minimal PATH with an old system python3), and keeps
    the pane open on error instead of vanishing."""
    tool = TOOL_FOR.get(os.path.basename(argv[0]))
    inner = (f"{shlex.quote(sys.executable)} {shlex.quote(drip_bin())} watch"
             + (f" --until-pid {pid}" if pid else "")
             + (f" --until-pidfile {shlex.quote(pidfile)}" if pidfile else "")
             + (f" --tool {tool}" if tool else ""))
    fallback = "echo; echo 'drip watch hit an error (see above). Press return to close.'; read _"
    return "/bin/sh -c " + shlex.quote(f"{inner} || {{ {fallback}; }}")


def terminal():
    tp = os.environ.get("TERM_PROGRAM", "")
    if os.environ.get("TMUX"):
        return "tmux"
    if tp == "ghostty" or os.environ.get("GHOSTTY_RESOURCES_DIR"):
        return "ghostty"
    return {"iTerm.app": "iterm", "WarpTerminal": "warp", "Apple_Terminal": "apple"}.get(tp, "other")


def osascript(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def as_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def tmux_split_args(layout):
    return ["-h", "-l", str(SIDE_COLS)] if layout == "side" else ["-v", "-l", str(STRIP_ROWS)]


def split_tmux(watch, layout):
    r = subprocess.run(["tmux", "split-window", *tmux_split_args(layout), "-d", watch])
    return r.returncode == 0, ""


def split_ghostty(watch, layout):
    # Ghostty resizes splits in pixels; grow the agent pane a lot and let the
    # meter pane shrink to Ghostty's minimum.
    direction, grow = ("right", "right,500") if layout == "side" else ("down", "down,10000")
    return osascript(f'''
tell application "Ghostty"
  set t1 to focused terminal of selected tab of front window
  set cfg to new surface configuration
  set command of cfg to {as_str(watch)}
  set t2 to split t1 direction {direction} with configuration cfg
  try
    perform action "resize_split:{grow}" on t1
  end try
  focus t1
end tell''')


def split_iterm(watch, layout):
    how, size = ("vertically", f"set columns to {SIDE_COLS}") if layout == "side" \
        else ("horizontally", f"set rows to {STRIP_ROWS}")
    return osascript(f'''
tell application "iTerm2"
  set s1 to current session of current window
  tell s1
    set s2 to (split {how} with default profile command {as_str(watch)})
  end tell
  try
    tell s2 to {size}
  end try
  select s1
end tell''')


def warp_tab(argv):
    """Warp can't split the current tab from outside; open a new tab with both panes.
    The agent pane records its pid so the meter pane can exit when the agent does."""
    d = os.path.expanduser("~/.warp/tab_configs")
    os.makedirs(d, exist_ok=True)
    name = "drip-run"
    fd, pidfile = tempfile.mkstemp(prefix="drip-run-", suffix=".pid")
    os.close(fd)
    os.unlink(pidfile)  # the watcher waits for the agent pane to create it
    watch = watch_cmd(argv, pidfile=pidfile)
    agent = " ".join(shlex.quote(a) for a in argv)
    cmd = "/bin/sh -c " + shlex.quote(f"echo $$ > {shlex.quote(pidfile)}; exec {agent}")
    with open(os.path.join(d, name + ".toml"), "w") as f:
        f.write(f'''name = "{name}"
[[panes]]
id = "root"
split = "horizontal"
children = ["agent", "drip"]
[[panes]]
id = "agent"
type = "terminal"
directory = {as_str(os.getcwd())}
commands = [{as_str(cmd)}]
is_focused = true
[[panes]]
id = "drip"
type = "terminal"
commands = [{as_str(watch)}]
''')
    r = subprocess.run(["open", f"warp://tab_config/{name}"])
    return r.returncode == 0, ""


def meter_window(watch, layout):
    """Terminal.app has no splits: open a small meter window instead."""
    return osascript(f'''
tell application "Terminal"
  set w to do script {as_str(watch)}
  delay 0.2
  set number of rows of front window to {16 if layout == "side" else STRIP_ROWS}
  set number of columns of front window to {SIDE_COLS + 6 if layout == "side" else 90}
end tell''')


def main(argv, layout="side"):
    if not argv:
        print("usage: drip run <command> [args...]   e.g. drip run codex", file=sys.stderr)
        return 2
    path = resolve(argv[0])
    if not path:
        print(f"drip run: command not found: {argv[0]}", file=sys.stderr)
        return 127
    argv = [path] + argv[1:]
    pid = os.getpid()  # we exec the agent below, so it keeps this pid
    watch = watch_cmd(argv, pid)
    term = terminal()
    ok, err = False, ""
    if term == "tmux":
        ok, err = split_tmux(watch, layout)
    elif term == "ghostty":
        ok, err = split_ghostty(watch, layout)
    elif term == "iterm":
        ok, err = split_iterm(watch, layout)
    elif term == "warp":
        ok, err = warp_tab(argv)
        if ok:
            print("💧 opened a new Warp tab with the agent and the meter side by side")
            return 0
    elif shutil.which("tmux") and not os.environ.get("DRIP_NO_TMUX"):
        cmd = " ".join(shlex.quote(a) for a in argv)
        os.execvp("tmux", ["tmux", "new-session", f"{cmd}; tmux kill-session", ";",
                           "split-window", *tmux_split_args(layout), "-d", watch_cmd(argv)])
    elif term == "apple":
        ok, err = meter_window(watch, layout)
    if not ok:
        hint = "split your terminal and run: drip watch"
        print(f"💧 couldn't open the meter automatically ({term}{': ' + err if err else ''}); {hint}", file=sys.stderr)
    os.execvp(argv[0], argv)

"""`drip run <cmd>` — run an agent CLI with a live water meter beside it.

Picks the best layout the current terminal can script:
  tmux (inside or installed)  thin 3-row meter under the agent
  Ghostty 1.3+ / iTerm2       AppleScript split of the current tab, meter underneath
  Warp                        new tab from a Tab Config: agent + meter side by side
  Terminal.app / other        small separate meter window, or just a tip
The meter pane exits by itself when the agent exits (--until-pid).
"""
import os
import shlex
import shutil
import subprocess
import sys

TOOL_FOR = {"codex": "codex", "claude": "claude-code"}


def drip_bin():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "drip")


def watch_cmd(argv, pid=None):
    tool = TOOL_FOR.get(os.path.basename(argv[0]))
    return (f"{shlex.quote(drip_bin())} watch" + (f" --until-pid {pid}" if pid else "")
            + (f" --tool {tool}" if tool else ""))


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


def split_tmux(watch):
    r = subprocess.run(["tmux", "split-window", "-v", "-l", "3", "-d", watch])
    return r.returncode == 0, ""


def split_ghostty(watch):
    return osascript(f'''
tell application "Ghostty"
  set t1 to focused terminal of selected tab of front window
  set cfg to new surface configuration
  set command of cfg to {as_str(watch)}
  set t2 to split t1 direction down with configuration cfg
  try
    perform action "resize_split:down,10000" on t1
  end try
  focus t1
end tell''')


def split_iterm(watch):
    return osascript(f'''
tell application "iTerm2"
  set s1 to current session of current window
  tell s1
    set s2 to (split horizontally with default profile command {as_str(watch)})
  end tell
  try
    tell s2 to set rows to 3
  end try
  select s1
end tell''')


def warp_tab(argv, watch):
    """Warp can't split the current tab from outside; open a new tab with both panes."""
    d = os.path.expanduser("~/.warp/tab_configs")
    os.makedirs(d, exist_ok=True)
    name = "drip-run"
    cmd = " ".join(shlex.quote(a) for a in argv)
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


def meter_window(watch):
    """Terminal.app has no splits: open a small meter window instead."""
    return osascript(f'''
tell application "Terminal"
  set w to do script {as_str(watch)}
  delay 0.2
  set number of rows of front window to 3
  set number of columns of front window to 90
end tell''')


def main(argv):
    if not argv:
        print("usage: drip run <command> [args...]   e.g. drip run codex", file=sys.stderr)
        return 2
    if not shutil.which(argv[0]):
        print(f"drip run: command not found: {argv[0]}", file=sys.stderr)
        return 127
    pid = os.getpid()  # we exec the agent below, so it keeps this pid
    watch = watch_cmd(argv, pid)
    term = terminal()
    ok, err = False, ""
    if term == "tmux":
        ok, err = split_tmux(watch)
    elif term == "ghostty":
        ok, err = split_ghostty(watch)
    elif term == "iterm":
        ok, err = split_iterm(watch)
    elif term == "warp":
        ok, err = warp_tab(argv, watch_cmd(argv))
        if ok:
            print("💧 opened a new Warp tab with the agent and the meter side by side")
            return 0
    elif shutil.which("tmux") and not os.environ.get("DRIP_NO_TMUX"):
        cmd = " ".join(shlex.quote(a) for a in argv)
        os.execvp("tmux", ["tmux", "new-session", f"{cmd}; tmux kill-session", ";",
                           "split-window", "-v", "-l", "3", "-d", watch_cmd(argv)])
    elif term == "apple":
        ok, err = meter_window(watch)
    if not ok:
        hint = "split your terminal and run: drip watch"
        print(f"💧 couldn't open the meter automatically ({term}{': ' + err if err else ''}); {hint}", file=sys.stderr)
    os.execvp(argv[0], argv)

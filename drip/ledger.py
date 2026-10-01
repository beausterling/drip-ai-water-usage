"""SQLite ledger of per-response token usage, fed incrementally from agent transcripts.

Only token counts are stored; water is computed at read time so coefficient
changes re-price all history.
"""
import glob
import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.expanduser("~/.local/share/drip/usage.db")
CLAUDE_ROOT = os.path.expanduser("~/.claude/projects")
CODEX_ROOTS = [os.path.expanduser("~/.codex/sessions"), os.path.expanduser("~/.codex/archived_sessions")]

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, offset INTEGER, size INTEGER, state TEXT);
CREATE TABLE IF NOT EXISTS usage (
  key TEXT PRIMARY KEY, tool TEXT, session TEXT, model TEXT, ts TEXT, day TEXT, project TEXT,
  input INTEGER, output INTEGER, cache_read INTEGER, cache_write INTEGER);
CREATE INDEX IF NOT EXISTS usage_session ON usage(session);
CREATE INDEX IF NOT EXISTS usage_day ON usage(day);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


def connect(path=DB_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    return db


def local_day(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().date().isoformat()
    except (ValueError, AttributeError):
        return None


# ---------- transcript parsers: (lines, state) -> rows ----------

def parse_claude(path, lines, state):
    """Claude Code: one row per API response, keyed by message id (a response is
    written as several lines that repeat the same usage block)."""
    parts = path.split(os.sep)
    session = parts[-3] if "subagents" in parts else os.path.splitext(parts[-1])[0]
    for line in lines:
        if '"usage"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get("message") or {}
        u = m.get("usage")
        model = m.get("model")
        if d.get("type") != "assistant" or not u or not model or model.startswith("<"):
            continue
        key = "cc:" + (m.get("id") or d.get("requestId") or d.get("uuid"))
        ts = d.get("timestamp")
        yield (key, "claude-code", session, model, ts, local_day(ts), d.get("cwd"),
               u.get("input_tokens") or 0, u.get("output_tokens") or 0,
               u.get("cache_read_input_tokens") or 0, u.get("cache_creation_input_tokens") or 0)


def parse_codex(path, lines, state):
    """Codex CLI: cumulative `token_count` totals; each increase becomes a row,
    attributed to the model from the latest `turn_context`. Codex input_tokens
    includes cached tokens, so uncached = input - cached."""
    for line in lines:
        if '"session_meta"' not in line and '"turn_context"' not in line and '"token_count"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        p = d.get("payload") or {}
        t = d.get("type")
        if t == "session_meta" and "cwd" not in state:
            # Only the first header: subagent rollouts also embed their parent's session_meta.
            state["cwd"] = p.get("cwd")
        elif t == "turn_context":
            state["model"] = p.get("model") or state.get("model")
        elif t == "event_msg" and p.get("type") == "token_count":
            tot = ((p.get("info") or {}).get("total_token_usage")) or {}
            if not tot:
                continue
            cur = {k: tot.get(k) or 0 for k in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens")}
            prev = state.get("last") or {k: 0 for k in cur}
            if sum(cur.values()) < sum(prev.values()):  # counter reset
                prev = {k: 0 for k in cur}
            delta = {k: max(0, cur[k] - prev[k]) for k in cur}
            state["last"] = cur
            if not any(delta.values()):
                continue
            session = codex_session_id(path)
            ts = d.get("timestamp")
            cached, cw = delta["cached_input_tokens"], delta["cache_write_input_tokens"]
            yield (f"cx:{session}:{tot.get('total_tokens') or sum(cur.values())}", "codex", session,
                   state.get("model") or "gpt-unknown", ts, local_day(ts), state.get("cwd"),
                   max(0, delta["input_tokens"] - cached - cw), delta["output_tokens"], cached, cw)


def codex_session_id(path):
    """rollout-2026-09-25T14-11-30-<uuid>.jsonl -> <uuid>"""
    stem = os.path.splitext(os.path.basename(path))[0]
    parts = stem.split("-")
    return "-".join(parts[-5:]) if len(parts) > 5 else stem


def discover():
    for p in glob.glob(os.path.join(CLAUDE_ROOT, "**", "*.jsonl"), recursive=True):
        yield p, parse_claude
    for root in CODEX_ROOTS:
        for p in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
            yield p, parse_codex


def parser_for(path):
    return parse_codex if os.path.abspath(path).startswith(os.path.expanduser("~/.codex")) else parse_claude


def ingest(db, path, parser=None):
    """Read new bytes of one transcript. Returns rows inserted."""
    parser = parser or parser_for(path)
    try:
        size = os.path.getsize(path)
    except OSError:
        return 0
    row = db.execute("SELECT offset, size, state FROM files WHERE path=?", (path,)).fetchone()
    offset, state = (row[0], json.loads(row[2] or "{}")) if row else (0, {})
    if row and row[1] == size:
        return 0
    if size < offset:  # truncated/rewritten: reparse; primary keys dedupe
        offset, state = 0, {}
    with open(path, "rb") as f:
        f.seek(offset)
        chunk = f.read()
    end = chunk.rfind(b"\n") + 1  # leave a partially-written last line for next time
    lines = chunk[:end].decode("utf-8", "replace").splitlines()
    rows = list(parser(path, lines, state))
    before = db.total_changes
    db.executemany("INSERT OR IGNORE INTO usage VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?)", (path, offset + end, offset + end, json.dumps(state)))
    return db.total_changes - before - 1


def sync(db, paths=None):
    n = 0
    for path, parser in (((p, None) for p in paths) if paths is not None else discover()):
        n += max(0, ingest(db, path, parser))
    db.execute("INSERT OR REPLACE INTO meta VALUES ('last_sync', ?)", (datetime.now().isoformat(),))
    db.commit()
    return n


def claude_session_files(transcript_path):
    """The main transcript plus any subagent transcripts for the same session."""
    base = os.path.splitext(transcript_path)[0]
    return [transcript_path] + glob.glob(os.path.join(base, "subagents", "*.jsonl"))

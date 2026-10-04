import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from drip import ledger
from drip.coeffs import Coefficients, Tokens


def write(path, events):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.writelines(json.dumps(e) + "\n" for e in events)


def cc(mid, model="claude-opus-5-5", i=10, o=20, cr=1000, cw=100):
    return {"type": "assistant", "timestamp": "2026-09-27T12:00:00Z", "cwd": "/x",
            "message": {"id": mid, "model": model, "usage": {
                "input_tokens": i, "output_tokens": o,
                "cache_read_input_tokens": cr, "cache_creation_input_tokens": cw}}}


def cx_count(inp, cached, out, total=None):
    u = {"input_tokens": inp, "cached_input_tokens": cached, "cache_write_input_tokens": 0,
         "output_tokens": out, "total_tokens": total if total is not None else inp + out}
    return {"type": "event_msg", "timestamp": "2026-09-27T12:00:00Z",
            "payload": {"type": "token_count", "info": {"total_token_usage": u}}}


class DripTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = ledger.connect(os.path.join(self.tmp, "t.db"))

    def sums(self, where="1=1"):
        return self.db.execute(f"SELECT SUM(input),SUM(output),SUM(cache_read),SUM(cache_write),COUNT(*) FROM usage WHERE {where}").fetchone()

    def test_claude_dedupes_and_includes_subagents(self):
        main = os.path.join(self.tmp, "proj", "S1.jsonl")
        write(main, [cc("a"), cc("a"), cc("a"), cc("b"), {"type": "user"},
                     cc("c", model="<synthetic>")])
        write(os.path.join(self.tmp, "proj", "S1", "subagents", "agent-1.jsonl"), [cc("d", model="claude-sonnet-5")])
        ledger.sync(self.db, [(p) for p in ledger.claude_session_files(main)])
        self.assertEqual(self.sums("session='S1'"), (30, 60, 3000, 300, 3))

    def test_incremental_append_and_partial_line(self):
        p = os.path.join(self.tmp, "proj", "S2.jsonl")
        write(p, [cc("a")])
        with open(p, "a") as f:
            f.write(json.dumps(cc("b"))[:20])  # half-written line
        ledger.sync(self.db, [p])
        self.assertEqual(self.sums()[4], 1)
        with open(p, "a") as f:
            f.write(json.dumps(cc("b"))[20:] + "\n")
        ledger.sync(self.db, [p])
        self.assertEqual(self.sums()[4], 2)

    def test_codex_deltas_subtract_cached(self):
        home = os.path.expanduser("~/.codex")
        p = os.path.join(self.tmp, "rollout-2026-09-27T12-00-00-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.jsonl")
        write(p, [{"type": "session_meta", "payload": {"id": "parent", "cwd": "/x"}},
                  {"type": "turn_context", "payload": {"model": "gpt-5.6-sol"}},
                  cx_count(1000, 0, 50), cx_count(1000, 0, 50),  # repeat -> no new row
                  cx_count(3000, 1500, 80),
                  {"type": "session_meta", "payload": {"id": "someone-else"}}])
        rows = list(ledger.parse_codex(p, open(p).read().splitlines(), {}))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][2], "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        self.assertEqual(rows[1][3], "gpt-5.6-sol")
        self.assertEqual(rows[1][7:], (500, 30, 1500, 0))  # 2000 new input, 1500 of it cached

    def test_codex_forked_snapshot_ignored(self):
        p = os.path.join(self.tmp, "rollout-x-11111111-2222-3333-4444-555555555555.jsonl")
        write(p, [cx_count(0, 0, 0, total=89208)])
        self.assertEqual(list(ledger.parse_codex(p, open(p).read().splitlines(), {})), [])

    def test_reference_session_matches_research(self):
        # RESEARCH.md §0: 2M cache-read / 100K in / 50K out ≈ 390 mL at MID for the reference model
        c = Coefficients()
        ml = c.water_ml(Tokens(100_000, 50_000, 2_000_000, 0), "unknown-model", "mid")
        self.assertAlmostEqual(ml, 390, delta=10)
        self.assertLess(c.water_ml(Tokens(0, 1000), "x", "mid", onsite=True), c.water_ml(Tokens(0, 1000), "x"))


    def test_watch_line_fits_narrow_panes(self):
        import re
        from drip import watch
        snap = {"ml": 412.0, "today": 3100.0, "series": [0.0] * 29 + [12.0], "rate": 2.4,
                "model": "gpt-6-astra", "tool": "codex", "project": "x", "session": "s"}
        for cols in (30, 60, 120):
            line = re.sub(r"\x1b\[[0-9;]*m", "", watch.line_view(snap, cols))
            self.assertLessEqual(len(line) + 1, cols)

    def test_first_run_welcome_only_on_bare_drip(self):
        from unittest import mock
        from drip import cli
        with mock.patch.object(cli, "INSTALLED_MARKER", os.path.join(self.tmp, "installed")), \
                mock.patch.object(sys.stdout, "isatty", return_value=True), \
                mock.patch.object(cli, "cmd_install", return_value=0) as install, \
                mock.patch.object(cli, "cmd_explain", return_value=None) as explain, \
                mock.patch.object(cli, "cmd_overview", return_value=None):
            cli.main(["explain"])
            install.assert_not_called()
            explain.assert_called_once()
            cli.main([])
            install.assert_called_once()


if __name__ == "__main__":
    unittest.main()

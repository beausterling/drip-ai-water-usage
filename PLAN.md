# drip — water meter for terminal AI agents (build plan)

Working name: `drip`. Python 3, stdlib only (same as `~/.claude/statusline.py`), so it runs anywhere without installs.

## Scope decisions (from Beau, 2026-09-27)
- **Inference only.** Count input / output / cache tokens. **No training amortization.**
- **Per-model coefficients** where models differ meaningfully (e.g. Opus vs Haiku vs GPT-5.x).
- Full operational water (on-site cooling + off-site electricity generation) by default; `--onsite` toggle for comparing with Google/OpenAI-style figures.
- LOW / MID / HIGH bands; MID shown by default.

## Coefficient model
```
mL = Σ tokens_type/1000 × Wh_per_1K[type] × model_multiplier × WF[band]
WF (L/kWh): LOW 1.42 · MID 3.57 · HIGH 5.48   (onsite-only: 0.13 · 0.435 · 0.958)
Wh/1K (frontier anchor, MID): input 0.20 · output 1.0 · cache-read 0.020 · cache-write 0.25
```
Source: RESEARCH.md §4.2, §5.

**Per-model multipliers.** No provider publishes per-model energy, so the only usable signal is relative list price (the method Couch and Hausfather use). The multiplier is set by output price relative to the anchor, and each model's cache-read ratio follows that model's own cache pricing (e.g. Opus 5.5 at 0.05×, not 0.1×). The table lives in `coefficients.toml` with a `last_reviewed` date and a source note per row. Unknown models fall back to the anchor and are flagged `~` in the UI.

| Family | Initial multiplier idea |
|---|---|
| Haiku | ~0.33× |
| Sonnet | 1.0× (anchor) |
| Opus | ~1.67× |
| Fable / Mythos | from price |
| GPT-5.x (Codex) | from price; `cached_input_tokens` → cache-read |
| Local (Ollama) | 0, or a separate "your own electricity" mode later |

## Data sources (token counts are real, not guessed)
- **Claude Code:** the status-line stdin JSON gives `transcript_path` and `session_id`. Sum `message.usage` from assistant entries in the transcript JSONL. Two gotchas:
  - Dedupe by `message.id` + `requestId`: one API response is written as several lines with the same usage.
  - Include subagent transcripts, which live in the session's `subagents/` directory, or subagent work is missed.
- **Codex CLI:** `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` → `token_count` events. Take the final `total_token_usage` per session. Note that `input_tokens` **includes** `cached_input_tokens`, so uncached = input − cached. Output includes reasoning tokens.
- Later adapters: Gemini CLI, opencode, Aider, and others as needed.

## Components
1. `drip/core.py`: coefficients loader, model matcher, `water(tokens, model, band)`.
2. `drip/adapters/{claude,codex}.py`: incremental JSONL parsers. They remember a byte offset per file, so each status-line tick only reads new lines (the status line runs often, so it must stay under about 50 ms).
3. **Ledger:** SQLite at `~/.local/share/drip/usage.db` with one row per (tool, session, model, day), holding token counts by type. Water is computed at read time, so changing coefficients recalculates all history.
4. **Status-line segment:** `💧 412 mL · 1.7 glasses`, plus an optional `(today 2.3 L)`. Appended as a segment to the existing `~/.claude/statusline.py`; nothing gets replaced. Also a standalone `drip statusline` for other tools.
5. **CLI:**
   - `drip session` — the current or last session.
   - `drip history --by day|week|month|model|tool` — tables plus sparklines.
   - `drip backfill` — imports all existing Claude Code and Codex transcripts, so history starts populated.
   - `drip explain` — shows the math and sources for any number.
   - Flags: `--band low|mid|high`, `--onsite`.
6. **Relatable units:** glass (250 mL), 500 mL bottle, toilet flush, shower-minute. Sources are in RESEARCH.md §8.

## Build order
1. Core, the Claude adapter and a session total, checked against the RESEARCH.md reference session.
2. Status-line segment wired into the current status line.
3. Ledger, backfill and history CLI.
4. Codex adapter.
5. Tests (fixture transcripts), README with methodology and caveats, then optionally package for others (`pipx install`, or a Claude Code plugin).

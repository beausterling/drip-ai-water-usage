# drip 💧

**How much water is your AI agent drinking?** drip estimates the water used by
terminal AI agents (Claude Code and Codex CLI) and shows it live in your status
line, a split-pane meter, or a full breakdown page, with every number traced
back to published research.

```
Opus 5.5 │ my-project │ ████░░░░░░ 48% │ 💧 412 mL (1.7 glasses) · today 3.1 L
```

- **Real token counts.** drip reads your agent's local logs, so the token counts aren't guesses.
- **Research-backed coefficients.** Low, mid and high estimates, each with its source cited.
- **Private.** Everything is local: no accounts, no telemetry, and nothing leaves your machine.
- **No dependencies.** Python 3.11+ standard library only.

## Install

```sh
git clone https://github.com/beausterling/drip-ai-water-usage.git ~/.drip
~/.drip/bin/drip install
```

`install` plays a short intro, imports your existing Claude Code and Codex
history, puts `drip` on your PATH (via `~/.local/bin`), and turns on the Claude
Code status line. If you already have a custom status line, it shows the line to
add instead of replacing yours.

## Ways to see it

| Where | How |
|---|---|
| **Claude Code status line** | Automatic after install. **Cmd+click** the 💧 to open the full breakdown (iTerm2, Ghostty, WezTerm, Kitty). |
| **Codex CLI / any agent** | `drip run codex` opens the agent with a live meter beside it (details below). |
| **Live meter, any terminal** | Split your terminal and run `drip watch`. A short pane becomes a one-line bar; a tall one shows a filling bottle. |
| **Browser breakdown** | `drip open`: this session by model and token type, the uncertainty range, 30-day history, the methodology, and sources. |
| **Inside Claude Code** | Type `!drip` for a text breakdown (uses no model tokens). |

`drip run` uses whatever layout your terminal supports:

| Terminal | Layout |
|---|---|
| Ghostty 1.3+ / iTerm2 | Splits the current tab, with a meter panel beside it (`--layout strip` for a one-line bar underneath) |
| Warp | Opens a new tab with the agent and the meter side by side |
| tmux | A meter panel beside the agent (or a 3-row strip with `--layout strip`) |
| macOS Terminal | A small separate meter window |

The meter closes automatically when the agent exits. So far only the iTerm2 setup has been tested by hand. The others follow each terminal's documentation; please open an issue if one misbehaves.

## Commands

```
drip                          this session + today + last 14 days
drip open                     browser breakdown
drip watch [--tool codex]     live meter for a split pane
drip run <cmd>                run an agent with the meter beside it
drip history --by day|week|month|model|tool|project [--days N]
drip session [ID]             per-model breakdown + low/mid/high range
drip explain [MODEL]          mL per 1K tokens and where each number comes from
drip splash                   replay the intro animation
drip sync                     import new log data (usually automatic)

--band low|mid|high           default mid (or DRIP_BAND)
--onsite                      count data-center cooling water only (or DRIP_ONSITE=1)
DRIP_LINKS=0                  turn off the clickable status-line link
```

## How the estimate works

```
water (mL) = tokens × energy per token (Wh) × water per kWh (L/kWh)
water per kWh = on-site cooling (WUE ÷ PUE) + water used to generate the electricity (EWIF)
```

- **Token counts:**
  - Claude Code: transcripts in `~/.claude/projects`, including subagents, counted once per API response.
  - Codex: rollout logs in `~/.codex/sessions`.
- **Energy per token:** based on measured inference energy (ML.ENERGY, Microsoft
  in *Joule*, Google) and Claude Code-specific analyses. Cache reads are counted
  at a fraction of normal input.
- **Water per kWh:** based on LBNL's 2024 US data center report, Li et al.
  ("Making AI Less Thirsty", *CACM* 2025), and provider disclosures.
- **Per-model scaling:** uses list price, the only public signal of relative
  serving cost. Models drip doesn't know show a `~`.
- **Scope:** inference only. Training and hardware manufacturing are excluded.

The full derivation is in [RESEARCH.md](RESEARCH.md), and every source is linked
on the breakdown page. The coefficients live in
[`drip/coefficients.toml`](drip/coefficients.toml). To override them, copy the
file to `~/.config/drip/coefficients.toml`. drip stores only token counts
(`~/.local/share/drip/usage.db`) and computes water when you view it, so edited
coefficients re-price all of your history.

## How accurate is it?

- **Token counts:** exact.
- **Water:** an estimate. The high estimate is about 10–30× the low one, because
  no AI provider publishes energy per token. The biggest unknown is the energy
  cost of cache reads, which make up most of an agent's tokens.
- **Reliable:** trends and comparisons with yourself ("3× more than last week").
- **Not reliable:** exact litres, or comparisons between models.

## Support

drip is free and MIT-licensed. If it's useful, you can chip in on Gumroad (link coming soon).

## Development

```sh
python3 -m unittest tests/test_drip.py
```

MIT © 2026 Beau Sterling

# LLM API List Prices (USD per 1M tokens)

Retrieved 2026-09-27. Standard (non-batch, non-fast, global/non-regional) first-party API rates.

| Provider | Model ID | Input | Output | Cached input (cache read/hit) | Cache write | Source |
|---|---|---|---|---|---|---|
| Anthropic | `claude-fable-5-1` | $10.00 | $50.00 | $0.25 (0.025x) | $12.50 (5m TTL) / $20.00 (1h TTL) | [1] |
| Anthropic | `claude-fable-5` | $10.00 | $50.00 | $1.00 | $12.50 (5m) / $20.00 (1h) | [1] |
| Anthropic | `claude-opus-5-5` | $4.00 | $20.00 | $0.20 (0.05x) | $5.00 (5m) / $8.00 (1h) | [1] |
| Anthropic | `claude-opus-5` | $5.00 | $25.00 | $0.50 | $6.25 (5m) / $10.00 (1h) | [1] |
| Anthropic | `claude-sonnet-5` | $2.00 | $10.00 | $0.20 | $2.50 (5m) / $4.00 (1h) | [1] |
| Anthropic | `claude-haiku-4-5` | $1.00 | $5.00 | $0.10 | $1.25 (5m) / $2.00 (1h) | [1] |
| OpenAI | `gpt-6-astra` | $10.00 (long ctx: $20.00) | $50.00 (long ctx: $75.00) | $1.00 (long ctx: $2.00) | $12.50 (long ctx: $25.00) | [2] |
| OpenAI | `gpt-6-luna` | $0.10 (long ctx: $0.20) | $0.50 (long ctx: $0.75) | $0.01 (long ctx: $0.02) | $0.125 (long ctx: $0.25) | [2] |
| OpenAI | `gpt-5.6-sol` | $4.00 (long ctx: $8.00) | $20.00 (long ctx: $30.00) | $0.40 (long ctx: $0.80) | $5.00 (long ctx: $10.00) | [2] |
| OpenAI | `gpt-5.6-terra` | $2.00 (long ctx: UNVERIFIED) | $12.00 (long ctx: UNVERIFIED) | $0.20 (long ctx: UNVERIFIED) | $2.50 (long ctx: UNVERIFIED) | [2] |

## Notes

**Anthropic** [1]
- 1M context at standard pricing for Claude 4.6+ (no long-context premium).
- Cache writes: 5-minute TTL = 1.25x base input, 1-hour TTL = 2x. Cache reads are 0.1x base, except Fable 5.1 (0.025x) and Opus 5.5 (0.05x).
- Sonnet 5: the $2/$10 launch price is now the standard price. The $3/$15 increase planned for 2026-09-01 was cancelled.
- Modifiers: Batch API is 50% off. `inference_geo: "us"` is 1.1x on every token category. Fast mode costs $8/$40 on Opus 5.5 and $10/$50 on Opus 5.
- Claude 4.7+ models (including Fable 5.x, Opus 5.x and Sonnet 5) use a newer tokenizer that produces about 30% more tokens for the same text than Sonnet 4.6 and earlier. Haiku 4.5 uses the old tokenizer, so per-token prices are not directly comparable to Haiku 4.5.

**OpenAI** [2]
- GPT-6 / GPT-5.6 models are priced in two bands, "short context" and "long context". The page does not say where the threshold is. Older models (gpt-5.5, gpt-5.4) are labelled "<272K context length", but that is not confirmed to apply to these models.
- `gpt-6-astra`, `gpt-6-luna` and `gpt-6-sol` are in the "Flagship models" table. `gpt-5.6-sol` is in the "Cyber models / Daybreak" table, and `gpt-daybreak-blue-latest` currently aliases it.
- `gpt-5.6-terra` is in the expanded "All models" table, which is collapsed by default and shows short-context prices only. Its long-context prices are not on the page. A WebFetch summary gave $4 / $0.40 / $5 / $18, but I could not verify that figure in the page source, so treat it as unconfirmed.
- The page says "GPT-5.6 Sol's promotional pricing is available at least through November 21, 2026", so the Sol prices may rise after that.
- Modifiers: Batch and Flex are 50% off. Fast mode (formerly Priority) is 2x. Data-residency (regional) endpoints add 10% for models released on or after 2026-03-05, and FedRAMP endpoints add 10%.
- A third-party article claimed `gpt-6-luna` is not a documented ID. The official pricing page does list `gpt-6-luna` ($0.10/$0.50), alongside a separate `gpt-5.6-luna` ($0.20/$1.20).

**Model size / active parameters:** Neither Anthropic nor OpenAI officially discloses parameter counts or active-parameter (MoE) sizes for any of these models. Third-party figures, such as a "5T MoE" claim for Opus 5, are speculation. Price tier is the only official signal of relative model scale.

## Sources
1. Anthropic pricing: https://platform.claude.com/docs/en/about-claude/pricing (also mirrored in the claude-api skill's model table, cached 2026-06-24)
2. OpenAI pricing: https://developers.openai.com/api/docs/pricing (redirect target of platform.openai.com/docs/pricing; openai.com/api/pricing returned HTTP 403)

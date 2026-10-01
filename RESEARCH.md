# Water Footprint of LLM Inference: Per-Token Coefficients for a Status-Line Meter

*Research compiled 2026-09-27. The goal is a defensible per-token water coefficient (mL per 1K tokens, split by input, output, cache-read and cache-write) for a Claude Code / agentic-CLI status-line add-on.*

**How to read this document**

- **[V] Verified.** I read the number in the primary source (paper PDF, official page or dataset). Where I quote a figure it appears verbatim or in a table in that source.
- **[S] Secondary.** The number comes from a secondary source, or from a primary source cited by another paper that I did not open myself.
- **[D] Derived.** This is my own arithmetic or assumption. The steps are shown.
- Units: 1 Wh × 1 L/kWh = 1 mL. That identity is used throughout.

---

## 0. TL;DR: recommended coefficients

These are full operational scope: on-site cooling water plus off-site electricity-generation water, measured as **consumption** (not withdrawal). Training and hardware manufacturing are excluded by default (see §6 for an optional uplift). The anchor is frontier-scale models (Sonnet/Opus class). All values are **[D]**.

| Token type (per 1K tokens) | LOW | **MID (default)** | HIGH |
|---|---|---|---|
| Input (uncached, prefill) | 0.071 mL | **0.72 mL** | 2.2 mL |
| Output (decode) | 0.43 mL | **3.6 mL** | 16.4 mL |
| Cache read (hit) | 0.0007 mL | **0.072 mL** | 0.55 mL |
| Cache write (creation) | 0.071 mL | **0.89 mL** | 2.7 mL |
| *Energy, output (Wh/1K)* | *0.3* | ***1.0*** | *3.0* |
| *Water factor (L per facility kWh)* | *1.42* | ***3.57*** | *5.48* |

**Reference session** (2M cache-read, 100K input, 50K output):

| | LOW | MID | HIGH |
|---|---|---|---|
| Water | ~30 mL | **~390 mL** (≈1.7 glasses) | ~2.1 L |
| Energy | ~21 Wh | ~110 Wh | ~390 Wh |

**On-site-only mode** is the boundary Google and (probably) OpenAI use. Multiply the numbers above by about 0.09 (LOW), **0.12 (MID)** or 0.17 (HIGH).

---

## 1. Summary table of sources

| # | Citation | Peer-reviewed? | Year | Headline number (as stated) | Units | Water scope | Model(s) |
|---|---|---|---|---|---|---|---|
| 1 | Li, Yang, Islam, Ren, "Making AI Less 'Thirsty'", *CACM* 68(7) / arXiv 2304.03271v5 | **Yes** (CACM) | 2023 → 2025 | GPT-3 needs a 500 mL bottle "for roughly 10–50 medium-length responses". US-avg **16.904 mL/request** (2.200 on-site + 14.704 off-site). Training **5.439 M L** total, 0.708 M L on-site **[V]** | mL/request; L | On-site + off-site (consumption) | GPT-3 175B |
| 2 | Elsworth et al. (Google), "Measuring the environmental impact of delivering AI at Google Scale", arXiv 2508.15734 | No (industry tech report) | 2025 | Median Gemini Apps text prompt: **0.24 Wh, 0.03 gCO2e, 0.26 mL** **[V]** | per prompt | **On-site only** (WUE 1.15 L/kWh) | Gemini Apps (mixed models) |
| 3 | Jegham et al., "How Hungry is AI?", arXiv 2505.09598v6 | Preprint (status not confirmed) | 2025 | Claude-3.7 Sonnet: **0.950 / 2.989 / 5.671 Wh** for 100in-300out / 1K-1K / 10K-1.5K. GPT-4o short **0.42 Wh** **[V]** | Wh/query | On-site + off-site (formula given) | 30 models incl. Claude 3.5/3.7, GPT-4o |
| 4 | Luccioni, Jernite, Strubell, "Power Hungry Processing", FAccT '24 / arXiv 2311.16863 | **Yes** | 2024 | Text generation mean **0.047 kWh per 1,000 inferences** (A100, models ≤ ~11B) **[V]** | kWh/1K inferences | Energy only | BLOOMz, Flan-T5, task models |
| 5 | Altman, "The Gentle Singularity" (blog) | No | Jun 2025 | "average query uses about **0.34 watt-hours** … about **0.000085 gallons** of water" **[V]** | per query | Unstated | ChatGPT default |
| 6 | You (Epoch AI), "How much energy does ChatGPT use?" | No (research org analysis) | Feb 2025 | **~0.3 Wh** per typical GPT-4o query; **~2.5 Wh** at 10K input; **~40 Wh** at 100K input **[V]** | Wh/query | Energy only | GPT-4o (assumed 100B active) |
| 7 | Mistral AI + Carbone 4 + ADEME, Mistral Large 2 LCA | Reviewed by consultancies (Resilio, Hubblo), not academic | Jul 2025 | 400-token Le Chat response: **1.14 gCO2e, 45 mL water**. Training + 18 months of use: **281,000 m³**, 20.4 ktCO2e **[V]** | per response | Lifecycle (incl. manufacturing/upstream) | Mistral Large 2 |
| 8 | Chung et al., "The ML.ENERGY Benchmark", NeurIPS 2025 D&B / arXiv 2505.06371. Leaderboard v3.0 data (Dec 2025) | **Yes** | 2025 | Measured GPU J per output token. E.g. DeepSeek-V3.1 8×B200 **0.61–8.57 J/tok** (batch 3072→8). Llama-3.1-405B 8×H100 **2.06–13.98 J/tok** **[V]** | J/output token | Energy (GPU only) | Open models, H100/B200 |
| 9 | Oviedo et al. (Microsoft), "Energy use of AI inference, efficiency pathways, and test-time scaling", *Joule* 2026 / arXiv 2509.20241 | **Yes** | 2026 | Frontier (>200B) on H100: median **0.31 Wh/query** (IQR 0.16–0.60), ~300 median output tokens. Long reasoning **3.91 Wh** **[V]** | Wh/query | Energy incl. PUE | DeepSeek-R1, Llama 405B, Nemotron 253B |
| 10 | Ruf & Detyniecki (AXA), "The Cost of Context", HotCarbon 2026 | **Yes** (workshop) | 2026 | Output/input token energy ratio **≈750–850×** under vLLM (batch 1, A100) **[V]** | ratio | Energy only | Llama-3.1-8B, Qwen2-7B |
| 11 | Morrison et al., "Holistically Evaluating the Environmental Impact of Creating LMs", ICLR 2025 | **Yes** | 2025 | OLMo series development + training: **2.769 M L** water. Embodied water **0.003 L/GPU-hr** **[V]** | L | Off-site (on-site = 0, closed loop) + embodied | OLMo 1B–13B |
| 12 | Shehabi et al., LBNL "2024 US Data Center Energy Usage Report" | Govt lab report (DOE) | Dec 2024 | Indirect water **4.52 L/kWh** (data-center-weighted). US grid avg **4.35 L/kWh**. Direct 66 B L (2023). Avg WUE ~0.36 L/kWh **[V]** | L/kWh | Both | US data centers |
| 13 | Microsoft datacenter efficiency page | No (corporate) | FY25 | Global **WUE 0.27 L/kWh**, **PUE 1.17** (FY25). Americas WUE 0.34 **[V]** | L/kWh | On-site | Azure |
| 14 | Amazon/AWS sustainability page | No (corporate) | 2025 | **WUE 0.12 L/kWh (withdrawal)**, **PUE 1.14** (2025). PUE 1.15 in 2024 **[V]** | L/kWh | On-site withdrawal | AWS |
| 15 | Google data centers page + ref #2 | No (corporate) | 2025 | Fleet **PUE 1.09** (2025). **WUE (consumptive) 1.15 L/kWh** (2023 and 2024, per #2) **[V]** | L/kWh | On-site | Google Cloud/TPU |
| 16 | Couch, "Electricity use of AI coding agents" (blog) | No | Jan 2026 | Claude Code: input **390**, output **1,950**, cache-read **39**, cache-write **490 Wh/MTok** (100K context). Median session **41 Wh** **[V]** | Wh/MTok | Energy only | Claude (inferred from Epoch + pricing) |
| 17 | Hausfather, "The real energy use of agentic AI" (The Climate Brink) | No | 2026 | 8 weeks of Claude Code, 3.2 B tokens: **~170 kWh (70–330)**, ~150 Wh/prompt. Tokens ~96% cache-read **[V]** | kWh | Energy only | Claude Code |
| 18 | Epoch AI, "What did it take to train Grok 4?" | No | 2025 | **310 GWh**, **~750 M L** water (1.8 L/kWh on-site + 158 gal/MWh gas generation) **[V]** | GWh, L | Both | Grok 4 (training) |
| 19 | Patterson et al., IEEE *Computer* 2022; Wu et al., MLSys 2022 | **Yes** | 2022 | Google ML energy: **60% inference / 40% training**. Meta AI capacity: **10:20:70** (experimentation:training:inference) **[S]** (via search summaries) | share | n/a | Fleet-level |
| 20 | Anthropic API pricing docs | n/a | Sep 2026 | Output = 5× input. Cache read = 0.1× input (0.05× Opus 5.5, 0.025× Fable/Mythos 5.1). 5-min write 1.25×, 1-h write 2× **[V]** | $/MTok | n/a | Claude models |

---

## 2. Key papers in detail

### 2.1 Li, Yang, Islam, Ren, "Making AI Less 'Thirsty'" (CACM July 2025; arXiv v5 Mar 2025) [V]

**Framework.** The paper uses the time-slotted operational water formula:

```
Water_operational = Σ_t e_t · [ ρ_s1,t  +  θ_t · ρ_s2,t ]
```

where:
- `e_t` is **server (IT) energy**
- `ρ_s1` is on-site WUE, in L per kWh of server energy
- `θ` is PUE
- `ρ_s2` is off-site EWIF, in L/kWh

On-site WUE is **not** multiplied by PUE, because WUE is already defined per IT kWh. Embodied (scope-3) water is amortized as `T·W/T0` over the server lifetime, but it is excluded from the case study for lack of data.

**Inference assumptions:**
- A "medium-sized request" has ≤800 words of input and 150–300 words of output.
- Per-request server energy is **0.004 kWh** (4 Wh). This comes from the GPT-3 paper's "0.4 kWh per 100 pages". The authors call it conservative and cite DynamoLLM: ~0.010 kWh/request for Llama-3-70B and ~0.016 kWh for Falcon-180B on DGX H100 under latency SLOs.

**Table 1 (verbatim excerpts):**

| Location | PUE | On-site WUE (L/kWh) | Off-site EWIF (L/kWh) | Water/request on-site (mL) | off-site | total | # requests per 500 mL |
|---|---|---|---|---|---|---|---|
| U.S. Average | 1.170 | 0.550 | 3.142 | 2.200 | 14.704 | **16.904** | 29.6 |
| Arizona | 1.180 | 1.630 | 4.959 | 6.520 | 23.406 | 29.926 | 16.7 |
| Texas | 1.280 | 0.250 | 1.287 | 1.000 | 6.590 | 7.590 | 65.9 |
| Virginia | 1.140 | 0.140 | 2.385 | 0.560 | 10.875 | 11.435 | 43.7 |
| Washington | 1.150 | 0.950 | 9.501 | 3.800 | 43.706 | 47.506 | 10.5 |
| Iowa | 1.160 | 0.140 | 3.104 | 0.560 | 14.403 | 14.963 | 33.4 |
| Ireland | 1.190 | 0.020 | 1.476 | 0.080 | 7.027 | 7.107 | 70.4 |

Check **[D]**: 4 Wh × (0.55 + 1.17 × 3.142) = 4 × 4.226 = 16.90 mL. This matches.

**Other verified figures from the paper:**
- Cooling towers evaporate "approximately 1–9 liters per kWh of server energy". Google's annualized global figure is ~1 L/kWh; a large commercial data center in Arizona summer reaches ~9 L/kWh.
- About 80% of withdrawal is consumed for cooling towers; about 70% for evaporative-assisted air cooling (Meta).
- US electricity: **withdrawal ~43.8 L/kWh** vs **consumption ~3.1 L/kWh** [8 = Reig et al./WRI]. The authors note that LBNL's 4.35 L/kWh is higher.
- Meta's self-reported scope-2 water for its fleet was **3.7 L/kWh** (2023).
- Scope-2 water is location-based. Renewable PPAs could lower market-based water.
- Training GPT-3 (1,287 MWh): **0.708 M L on-site, 4.731 M L off-site, 5.439 M L total** (US average).

**Interpretation.** The ~17 mL/request is almost entirely driven by the **4 Wh/request** energy assumption. Modern production estimates are 0.24–0.34 Wh (see §5). About 87% of the water is **off-site** (power generation).

### 2.2 Google, "Measuring the environmental impact of delivering AI at Google Scale" (Aug 2025) [V]

The median Gemini Apps text prompt (May 2025) under the "Comprehensive" boundary uses **0.24 Wh**:

| Component | Wh | Share |
|---|---|---|
| Active accelerators | 0.14 | 58% |
| Host CPU+DRAM | 0.06 | 25% |
| Idle machines | 0.02 | 10% |
| Overhead (PUE) | 0.02 | 8% |

Under the narrower "Existing" boundary it is 0.10 Wh. The paper notes that "a scaling of **1.72** would need to be applied to active AI accelerator energy consumption" to get full production energy.

**Water formula (verbatim):** `Water/prompt = (E_Total/prompt − E_Overhead/prompt) × WUE`. WUE is Google's fleet ISO Category-2 consumptive WUE, which was **1.15 L/kWh** in both 2023 and 2024. Check: (0.24 − 0.02) × 1.15 = 0.253 → **0.26 mL**.

**This is on-site cooling only.** No scope-2 (electricity-generation) water is included. The paper reports a 33× energy and 44× carbon reduction over 12 months. The **number of tokens in the "median prompt" is not disclosed**, so it cannot be turned into a per-token figure directly.

The paper also summarizes prior estimates:
- Li et al.: "approximately 10–50 mL per prompt"
- Altman: 0.34 Wh / 0.3 mL
- Mistral: 45 mL / 400-token response
- EcoLogits: 1.83–6.95 Wh for a 50-output-token prompt

### 2.3 Jegham et al., "How Hungry is AI?" (arXiv v6, Nov 2025) [V]

**Method:** API latency and tokens-per-second (from Artificial Analysis) × assumed GPU power × utilization × PUE. Batch size 8 is assumed. Unknown-size flagship models (GPT-4o, Claude) are classed as "Large" (8 GPUs). The numbers are **modeled, not measured.**

**Water formula:** `Water = E_query/PUE · WUE_site + E_query · WUE_source`. Here E_query already includes PUE.

Multipliers used for **Anthropic (assumed on AWS, DGX H200/H100)**:

| PUE | WUE on-site | WUE off-site | CIF |
|---|---|---|---|
| **1.14** | **0.18 L/kWh** | **5.11 L/kWh** | 0.287 kgCO2e/kWh |

For Azure/OpenAI the values are PUE 1.12, on-site 0.30 and off-site 4.35.

Energy (Table 4):

| Model | 100 in / 300 out | 1K / 1K | 10K / 1.5K |
|---|---|---|---|
| Claude-3.7 Sonnet | 0.950 Wh | 2.989 Wh | 5.671 Wh |
| Claude-3.5 Sonnet | 0.973 Wh | 3.638 Wh | 7.772 Wh |
| Claude-3.5 Haiku | 0.975 Wh | 4.464 Wh | 8.010 Wh |
| GPT-4o | 0.423 Wh | 1.215 Wh | 2.875 Wh |

**[D]** Applying their water formula to Claude-3.7 Sonnet gives **5.0 mL**, **15.8 mL** and **29.9 mL** for the three prompt sizes.

Validation: the authors say their GPT-4o short-prompt value of 0.42 Wh is within 19% of Altman's 0.34 Wh.

Caveats: batch-8 serving is far below production batch sizes (see ML.ENERGY data below). Haiku comes out *higher* than Sonnet, which suggests a throughput-based modeling artifact. **Treat these as an upper-band reference.**

### 2.4 Luccioni, Jernite, Strubell, "Power Hungry Processing" (FAccT 2024) [V]

- Setup: 8×A100-80GB on AWS, 1,000 inferences per dataset, energy measured with CodeCarbon.
- Text generation: **0.047 kWh per 1,000 inferences** on average, i.e. ~0.047 Wh per inference.
- Image generation: 2.9 kWh per 1,000.
- Classification: ~0.002 kWh per 1,000.

The models are small (≤ ~11B: BLOOMz, Flan-T5), so the paper is **not directly usable for frontier per-token coefficients**. It is useful for relative task intensity. It reports no water figures.

### 2.5 OpenAI / Sam Altman (June 2025) [V]

"the average query uses about 0.34 watt-hours … It also uses about 0.000085 gallons of water; roughly one fifteenth of a teaspoon."

**[D]** 0.000085 gal × 3,785 mL/gal = **0.32 mL**. That implies **~0.95 L/kWh**, a value consistent with **on-site-only** accounting, though no boundary or methodology is disclosed. Tokens per query are not disclosed.

### 2.6 Epoch AI (Josh You, Feb 2025) [V]

**Assumptions:**
- GPT-4o with ~100B active parameters
- 500 output tokens per query
- 2 FLOP per parameter per token
- H100 at 1,500 W including data-center overhead
- 10% compute utilization, 70% power utilization

**Results:**
- **~0.3 Wh/query**
- 10K-token input → **~2.5 Wh**
- 100K-token input → **~40 Wh** (attention cost grows quadratically)

**[D]** implied rates:
- Output ≈ 0.6 Wh/1K tokens
- At 10K context: (2.5 − 0.3)/10K ≈ 0.22 Wh per 1K input tokens
- At 100K context: ≈ 0.4 Wh per 1K input tokens

### 2.7 Mistral Large 2 lifecycle analysis (July 2025) [V]

- Method: AFNOR "Frugal AI" methodology, GHG Protocol Product Standard, ISO 14040/44. Built with Carbone 4 and ADEME, reviewed by Resilio and Hubblo.
- **Marginal per-response impact** ("400-token response", excluding user terminals): **1.14 gCO2e, 45 mL water, 0.16 mg Sb eq**.
- Training + 18 months of use: **20.4 ktCO2e, 281,000 m³ water**.
- The Batch (DeepLearning.AI) reports that training + inference account for **91% of water consumption** **[S]**.

The page does **not** disclose energy per response, data-center location or the split between phases for water. The metric is "Water Consumption Potential" (LCA), which includes upstream and manufacturing water. **It is not comparable** to operational-only figures (see §5).

### 2.8 ML.ENERGY Benchmark / Leaderboard v3.0 (Dec 2025) [V]

These are measured GPU energy per **output** token (`energy_per_token_joules`) from the leaderboard's public JSON (github.com/ml-energy/leaderboard, `public/data/models/*.json`, lm-arena-chat task). They are GPU-only, with no host, idle or PUE included:

| Model (active/total params) | HW | Batch 8 | Batch 128 | Largest batch |
|---|---|---|---|---|
| DeepSeek-V3.1 (37B/671B MoE) | 8×B200 | 8.57 J | 1.94 J | 0.61 J (bs 3072) |
| Qwen3-235B-A22B FP8 | 8×H100 | 11.39 J | 1.36 J | 0.74 J (bs 512) |
| Qwen3-235B-A22B FP8 | 2×B200 | 8.42 J | 0.82 J | 0.50 J (bs 256) |
| Llama-3.1-405B FP8 | 8×H100 | 13.98 J | 2.43 J | 2.06 J (bs 256) |
| Llama-3.1-405B FP8 | 4×B200 | 12.99 J | 1.77 J | 1.15 J (bs 512) |
| Llama-3.1-70B | 4×H100 | 3.76 J | 0.56 J | 0.37 J (bs 1024) |

The blog post for v3.0 reports B200 beating H100 in 88% of comparisons, with a median 35% energy reduction.

**[D]** 1 J/token = 0.278 Wh per 1K tokens. At realistic production batches (128–512), frontier-scale MoE and dense models use **~0.6–2.4 J per output token**, i.e. 0.17–0.68 Wh/1K (GPU only). Applying Google's 1.72× full-stack factor gives **~0.3–1.2 Wh per 1K output tokens.**

### 2.9 Oviedo et al. (Microsoft), *Joule* 2026 [V]

**Model:** `E_query = PUE · P_node · L_eff / (3.6 · TPS)`

- Node: 8×H100 with P_max 10.2 kW
- P_node ~ lognormal centered at 0.7·P_max
- PUE lognormal, P5–P95 range 1.05–1.40
- TPS from TensorRT-LLM benchmarks, continuous batching
- L_in fixed at 500, and L_eff ≈ L_out ("output tokens dominate energy use")

**Results:**
- Frontier (>200B) median **0.31 Wh/query** (IQR 0.16–0.60), with a median of 300 output tokens
- Test-time scaling (median 5,000 output tokens): **3.91 Wh**
- 8–20× line-of-sight efficiency gains
- Blackwell delivers 2.8–3.4× the TPS of H100

**[D]** ≈ **1.0 Wh per 1K output tokens** (H100, including PUE). The authors explicitly flag that prefill for long-context **agentic coding** is under-modeled: "in extreme scenarios (e.g., 100 thousand input tokens), prefill energy use will be substantially higher", while KV/conversation caching "significantly reduce[s] this effect".

### 2.10 Input vs output vs cache: direct evidence

- **HotCarbon 2026 (Ruf & Detyniecki) [V]:** under vLLM, an output token costs **≈750–850×** an input token in energy. This was measured on A100 with **no batching**. It is an upper bound on the ratio, because production batching cuts per-output-token energy by 10–20× (see the ML.ENERGY table: batch 8 → 128), while prefill is already compute-bound.
- **Vellaisamy et al., IISWC 2026 (arXiv 2608.28044) [V]:** energy decomposes into fixed prefill + setup + marginal per-token decode. Per-token energy falls sharply with longer outputs (Llama-3.2-1B, H200: 7.46 → 0.72 J/token as output goes from 10 to 512 tokens).
- **Anthropic pricing [V]:** output is 5× input; cache read is 0.1× input (0.05× on Opus 5.5, 0.025× on Fable/Mythos 5.1); cache write is 1.25× (5-minute) or 2× (1-hour). Price is **not** energy, but it is the only public signal of Anthropic's relative serving cost. Couch and Hausfather both use it.
- **Physics [D]:**
  - Prefill processes tokens in parallel and is compute-bound: ~2·N_active FLOPs per token plus attention.
  - Decode is memory-bandwidth-bound: every step re-reads weights and the KV cache, and is amortized only across the batch.
  - A cache read skips prefill compute. What remains is KV storage/transfer, HBM capacity held (which reduces batch size), and the attention that *new* tokens pay over the cached context.
  - The raw transfer energy for a 100K-token KV cache is tens of joules at most, which is small. Most of the "cost" of a cache hit is therefore capacity and attention, and is highly implementation-dependent.

### 2.11 Agentic-coding estimates (non-peer-reviewed, but directly on target)

- **Couch (Jan 2026) [V]:** back-solves Epoch's figures with the pricing ratio output = 5 × input.

  | Context | Input (Wh/MTok) | Output (Wh/MTok) |
  |---|---|---|
  | Short | 110 | 540 |
  | 10K | 200 | 990 |
  | 100K | 390 | 1,950 |

  Cache read is ~39 Wh/MTok (0.1×) and cache write ~490 Wh/MTok (1.25×). The author notes: "I have no idea if these are reasonable guesses." The median session is 41 Wh (24 requests, 592K tokens) and a typical heavy day is ~1.3 kWh.
- **Hausfather (2026) [V]:**
  - Usage: 1,138 prompts, 14,000+ model calls, 3.2 B tokens.
  - Token mix: ~96% cache reads, ~3.8% cache writes, ~0.4% output.
  - Energy: **~170 kWh (70–330)**, i.e. ~150 Wh/prompt.
  - Cache-read energy assumed at 10% of fresh input, with bounds of 1%–25%.
- **mdodkins gist (Mar 2026) [S]:** applies "2 mL/Wh" to Couch's 41 Wh and reports ~124 mL. The arithmetic is internally inconsistent (41 × 2 = 82), so it is not used here.

---

## 3. The water accounting framework

### 3.1 Definitions

- **Withdrawal:** water taken from a source. **Consumption:** withdrawal minus discharge, i.e. evaporated or otherwise removed from the local watershed (Li et al. [V]; LBNL [V]).
  - For cooling towers, ~80% of withdrawal is consumed (Google, via Li [V]; the Google paper [V] also states "On average, Google consumes 80% of the water withdrawn").
  - US power generation: **~43.8 L/kWh withdrawn vs ~3.1 L/kWh consumed** (Li [V], citing USGS/WRI). **Use consumption.** Withdrawal numbers overstate the impact by ~10× for thermoelectric once-through cooling.
- **Scope 1 / on-site:** data-center cooling water, measured as **WUE** in L per kWh of *IT* energy (The Green Grid; LBNL defines "WUE (site)" [V]).
- **Scope 2 / off-site:** water consumed generating the electricity, measured as **EWIF** (Li) or "WUE (source)" (LBNL, Jegham), in L per kWh of facility electricity. It is dominated by thermoelectric cooling and, depending on method, **hydro-reservoir evaporation**.
- **Scope 3 / embodied:** chip fabrication, construction, etc. This is poorly quantified. Morrison et al. estimate only **0.003 L per GPU-hour** for manufacturing (they call it a lower bound). Li notes that Apple reports 99% of its water footprint is supply chain.
- **PUE:** total facility energy / IT energy. It multiplies scope-2 water, not on-site WUE, because WUE is already per IT kWh.

### 3.2 Canonical formula

**[D]**, following Li et al. Let E_fac be facility energy (IT × PUE). Then:

```
Water (L) = E_IT · WUE_site + E_fac · EWIF
          = E_fac · ( WUE_site / PUE + EWIF )
```

- Morrison et al. use `P·PUE·(WUE_on + WUE_off)`, which slightly overcounts on-site water.
- Jegham uses the E_fac form shown above.
- The user-proposed form `energy × PUE × (WUE + EWIF)` matches Morrison's. It differs from Li's by ≤15% on the on-site term only, which is negligible next to other uncertainties.

### 3.3 Provider figures

| Provider | PUE | On-site WUE | Notes |
|---|---|---|---|
| **Google** | 1.09 (2025 fleet) [V] | **1.15 L/kWh** consumptive, 2023 and 2024 (Gemini paper) [V] | Highest on-site WUE of the three (heavy evaporative cooling), lowest PUE. 87% of 2025 withdrawal from low/medium-risk sources [V]. |
| **Microsoft Azure** | 1.16 (FY24), 1.17 (FY25) [V] | 0.30 (FY24), **0.27 L/kWh (FY25)** [V] | FY25 by region: Americas 0.34, APAC 0.25, EMEA 0.03 [V]. New designs since Aug 2024 are "zero water for cooling" (closed loop) [V, MS blog]. |
| **AWS** | 1.15 (2024), **1.14 (2025)** [V] | **0.12 L/kWh (2025, withdrawal)**, ~0.15 (2024) [V/S] | Ireland region 0.02. Consumption is ≤ withdrawal. Jegham used 0.18 (2023 report). |
| **Meta** | n/a | n/a | Scope-2 water **3.7 L/kWh** fleet (2023, via Li) [V] |
| **US average (LBNL)** | 1.4 all DCs (2023). Hyperscale lower. 1.15–1.35 projected 2028 [V] | **~0.36 L/kWh** avg (2023), rising to 0.45–0.48 [V]. Hyperscale median ~0.32–0.40 [V] | |
| **Li et al. (Microsoft sites)** | 1.11–1.43 | 0.00 (India) to 1.90 (Indonesia). US avg **0.55** [V] | |

**Off-site EWIF (consumption):**
- US average: **3.14 L/kWh** (WRI/Reig et al. 2020, used by Li) [V-via-Li]
- US average: **4.35 L/kWh** (LBNL, grid, includes hydro evaporation) [V]
- US data-center-weighted: **4.52 L/kWh** (LBNL) [V]
- Jegham used **5.11 L/kWh** for AWS-weighted regions and 4.35 for Azure [V]
- Regional spread across Microsoft sites: 1.29 (Texas) to 9.50 (Washington, hydro-heavy) [V]
- Morrison used 1.29 (Jupiter cluster, Texas) and 3.10 (Augusta) [V]
- Natural gas generation alone is ~158 gal/MWh ≈ 0.60 L/kWh (Epoch, Grok 4) [V]

**Why EWIF is so uncertain.** Whether hydro-reservoir evaporation is allocated to electricity is the main driver. It is why hydro-rich Washington gets 9.5 L/kWh. It is also location-based: renewable PPAs (wind/solar consume ~0) would cut market-based scope-2 water sharply, and no provider reports market-based scope-2 water.

### 3.4 Where Anthropic runs

Anthropic has published **no** per-query energy or water figures and no corporate scope 1/2/3 water disclosure. Several secondary sources state this, and I found no Anthropic disclosure.

Compute sources [S: CNBC, DCD, Nov 2025]:
- **AWS**: Project Rainier, ~500K Trainium2 chips, Indiana campus plus other sites
- **Google Cloud TPUs**: up to 1M TPUs, >1 GW in 2026
- **Microsoft Azure**: $30B commitment (NVIDIA)
- **Own facilities**: via Fluidstack in Texas and New York ($50B, from 2026)

A defensible blended on-site WUE is therefore somewhere between AWS (~0.12–0.18) and Google (1.15). Off-site water depends on Indiana (coal/gas-heavy MISO grid), Texas (ERCOT, Li EWIF 1.29) and New York.

---

## 4. Energy per token: input vs output vs cache

### 4.1 Evidence summary (facility-level where possible)

| Source | Energy per 1K output tokens (incl. overhead) | Notes |
|---|---|---|
| ML.ENERGY v3, frontier open models, bs 128–512 [V→D] | 0.17–0.68 Wh GPU-only → **~0.3–1.2 Wh** with 1.72× | Measured, B200/H100 |
| Epoch (GPT-4o) [V→D] | **~0.6 Wh** | 500 output tokens, 0.3 Wh |
| Oviedo/Microsoft, *Joule* [V→D] | **~1.0 Wh** (H100). ~0.35–0.4 on Blackwell | Median; IQR ≈ 0.5–2.0 |
| Couch (Claude, pricing-scaled) [V] | 0.54 (short) / 0.99 (10K) / **1.95 (100K ctx)** | Output rate grows with context |
| Jegham, Claude-3.7 Sonnet [V→D] | **~3 Wh** (0.95 Wh / 300 out; 2.99 Wh / 1K in+1K out) | Modeled at batch 8. Upper-band |
| Google Gemini median prompt [V] | 0.24 Wh/prompt, tokens unknown | Suggests the low end is plausible for mixed traffic |

### 4.2 Recommended energy coefficients [D]

Facility-level, including host, idle and PUE, frontier-scale (Sonnet/Opus class), long agentic contexts. Units are Wh per 1K tokens.

| | LOW | MID | HIGH | Basis |
|---|---|---|---|---|
| **Output** | 0.30 | **1.0** | 3.0 | See the rationale below |
| **Input (uncached)** | 0.05 | **0.20** | 0.40 | See the rationale below |
| **Cache read** (× input) | 1% → 0.0005 | **10% → 0.020** | 25% → 0.10 | See the rationale below |
| **Cache write** (× input) | 1.0× → 0.05 | **1.25× → 0.25** | 1.25× → 0.50 | See the rationale below |

**Output.**
- LOW matches ML.ENERGY measured batches with Blackwell, and Google/Epoch-level efficiency.
- MID matches Oviedo's median, ML.ENERGY Llama-405B H100 at batch 128 (2.43 J × 1.72 ≈ 1.16 Wh), and Couch at 10K context.
- HIGH matches Jegham's Claude values and Couch at 100K context.

**Input (uncached).**
- LOW is a physics estimate: 2×100B FLOPs at ~4×10¹⁴ effective FLOP/s per 700 W GPU ≈ 0.1 Wh/1K GPU-only for short context. I lower it for MoE and Blackwell.
- MID uses Couch's 10K-context rate (≈200) and the pricing ratio (1/5 of output).
- HIGH uses Epoch/Couch at 100K context (≈390).

**Cache read.**
- MID uses the standard Anthropic pricing ratio of 0.1×.
- The LOW–HIGH range (1%–25%) is Hausfather's bounds.
- Newer models price cache hits at 0.05× or 0.025×, which supports a lower LOW.

**Cache write.** A cache write is a prefill plus storage. The 1.25× comes from pricing. Energy is probably ≈ 1.0× input, which is used for LOW. The 1-hour TTL at 2× price reflects holding cost rather than compute, so it is not used for HIGH.

**Why this split matters for agentic coding [D].** In Hausfather's 3.2 B-token log, ~96% of tokens were cache reads and ~0.4% were output. Under MID, cache reads (0.02 Wh/1K) × 96% still contribute a large share of energy because there are so many of them. The cache-read multiplier is the **single most sensitive parameter** for a Claude Code meter: at HIGH (25%), cache reads dominate the session total.

**Tokenizer caveat [V].** Anthropic states that Claude 4.7+ models produce "approximately 30% more tokens for the same text". Per-token energy on newer models is therefore probably somewhat lower per token for the same work.

---

## 5. Derived coefficient model: step by step [D]

### Step 1: water factor per facility kWh

`WF = WUE_site / PUE + EWIF`

| Band | WUE_site (source) | PUE (source) | EWIF (source) | WF |
|---|---|---|---|---|
| LOW | 0.15 (AWS ~2024 [V/S]) | 1.15 (AWS 2024 [V]) | 1.29 (Li Texas / Morrison Jupiter, WRI [V]) | 0.130 + 1.29 = **1.42 L/kWh** |
| **MID** | **0.50** (blend: LBNL hyperscale 0.32–0.48 [V], Li US 0.55 [V], AWS/Azure/Google 0.12–1.15 [V]) | **1.15** | **3.14** (WRI US avg, via Li [V]) | 0.435 + 3.14 = **3.57 L/kWh** |
| HIGH | 1.15 (Google consumptive fleet [V]) | 1.20 | 4.52 (LBNL DC-weighted [V]) | 0.958 + 4.52 = **5.48 L/kWh** |

The on-site-only factor is 0.130 / **0.435** / 0.958 L/kWh.

### Step 2: water per 1K tokens = energy (Wh/1K) × WF (L/kWh), which gives mL/1K

| Token type | LOW | **MID** | HIGH |
|---|---|---|---|
| Input | 0.05 × 1.42 = **0.071** | 0.20 × 3.57 = **0.72** | 0.40 × 5.48 = **2.19** |
| Output | 0.30 × 1.42 = **0.43** | 1.00 × 3.57 = **3.57** | 3.00 × 5.48 = **16.4** |
| Cache read | 0.0005 × 1.42 = **0.0007** | 0.020 × 3.57 = **0.072** | 0.10 × 5.48 = **0.55** |
| Cache write | 0.05 × 1.42 = **0.071** | 0.25 × 3.57 = **0.89** | 0.50 × 5.48 = **2.74** |

On-site-only MID values: input 0.087, output 0.43, cache read 0.0087, cache write 0.11 mL/1K.

### Step 3: implementation

```text
mL = (in/1000)*C_in + (out/1000)*C_out + (cache_read/1000)*C_cr + (cache_write/1000)*C_cw
```

Claude Code transcripts and API `usage` blocks report `input_tokens`, `output_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens`. These map one-to-one onto the four coefficients.

Optional heuristic model-class multipliers [D] use the output price ratio:
- Haiku 4.5: $5/MTok → ×0.33 vs Sonnet
- Sonnet 4.x at $15 → ×1.0
- Opus 4.5+ at $25 → ×1.67

Price reflects margin and demand as well as compute, so treat these as rough. The MID anchor sits between Sonnet and Opus.

---

## 6. Training amortization (optional)

**Verified training water figures:**
- **GPT-3:** 1,287 MWh; 0.708 M L on-site, 5.44 M L total (Li [V])
- **OLMo family (1B–13B):** 2.769 M L including development runs. Development was ~50% of the impact (Morrison [V/S])
- **Mistral Large 2:** 281,000 m³ = 281 M L for training + 18 months of use (Mistral [V])
- **Grok 4:** 310 GWh, ~750 M L (Epoch [V])

Frontier Claude training energy is **undisclosed**.

**Three options:**

1. **Exclude (default).** This is marginal/operational accounting, the boundary Google (#2), Jegham (#3) and Li's per-request numbers use. Training is a sunk cost that one user's marginal token does not cause.
2. **Fleet-share uplift [D].** Scale operational water by (total ML energy / inference energy):
   - Google 2019–21: inference was 3/5 of ML energy [S], so ×1.67
   - Meta: 70% of AI capacity was inference [S], so ×1.43

   **Recommended toggle:** LOW ×1.0, **MID ×1.43**, HIGH ×1.67. Caveat: these splits predate the 2024–26 inference boom (reasoning, agents). Today the inference share is probably higher, so the uplift is probably smaller.
3. **Per-model [D].** `W_train / lifetime tokens`. Example: a 300 GWh run × 3.57 L/kWh ≈ 1.07 × 10⁹ L. Amortized over 10¹⁵ compute-weighted tokens that is ~1.1 mL/1K; over 10¹⁶ it is ~0.11 mL/1K. Lifetime token volumes for Claude models are not public, so **this is not recommended** without a disclosed denominator.

Embodied hardware water (Morrison: 0.003 L/GPU-hr) is **negligible** at ~10⁶ tokens per GPU-hour. The unknown chip-fab supply chain could be larger (Li: Apple's supply chain is 99% of its footprint), but no usable per-GPU figure exists.

---

## 7. Sanity checks

### 7.1 Reference Claude Code session: 2M cache-read, 100K input, 50K output

| | LOW | MID | HIGH |
|---|---|---|---|
| Cache reads | 1.4 mL | 143 mL | 1,096 mL |
| Input | 7.1 mL | 71.5 mL | 219 mL |
| Output | 21.3 mL | 178.7 mL | 822 mL |
| **Total water** | **~30 mL** | **~393 mL** | **~2,137 mL** |
| Energy | 21 Wh | 110 Wh | 390 Wh |
| On-site only | 2.7 mL | 48 mL | 374 mL |

Adding 150K cache-write tokens (typical at ~4% of tokens) gives 41 / **527** / 2,547 mL.

Cross-check: MID energy of 110 Wh is about half of Couch's rates applied to the same session (≈214 Wh: 78 + 39 + 97.5). Couch uses 100K-context rates throughout.

Cross-check against Hausfather's 8-week log (3.2 B tokens: 95.8% cache-read, 3.8% cache-write, 0.4% output):

| | LOW | MID | HIGH |
|---|---|---|---|
| Energy | 11.5 kWh | **105 kWh** | 406 kWh |
| Water | 16 L | **374 L** | 2,223 L |

Hausfather's own estimate is **170 kWh (70–330)**. MID falls inside his range.

### 7.2 Versus Google's 0.26 mL per prompt

For a chat-style prompt (~500 input, ~400 output tokens) at MID:
- Energy is **0.50 Wh**, about 2× Google's 0.24 Wh. Gemini's median prompt mixes Flash-class models and has an undisclosed, probably short, length.
- On-site-only water is **0.22 mL**, which is close to Google's 0.26 mL.
- Full-scope water is **1.8 mL**.

**The ~7× gap is almost entirely scope:** Google counts only cooling water (WUE 1.15). Off-site electricity water at ~3.1 L/kWh is roughly 3× larger than Google's on-site WUE, and PUE/WUE differences account for the rest. Altman's 0.32 mL for 0.34 Wh implies ~0.95 L/kWh, which is likewise consistent with on-site-only accounting.

### 7.3 Versus Li et al.'s 500 mL per 10–50 responses (≈10–50 mL each; US average 16.9 mL)

A Li-style request (~1,070 input and ~300 output tokens) at MID uses **0.51 Wh → 1.8 mL**. Li's water intensity is 16.9 mL / 4 Wh ≈ 4.2 L per server-kWh, versus MID 3.57 L per facility-kWh (≈4.1 per IT kWh). The water factors are **nearly identical**.

**The ~9× discrepancy is energy.** Li assumes **4 Wh per request**, based on GPT-3's 2020 "0.4 kWh/100 pages", while 2025 production measurements and estimates are 0.24–0.34 Wh. Li's "10–50 responses" range also spans site variation (7.1–47.5 mL per request in Table 1). Li's number is therefore best read as an *older-hardware, low-batching* upper bound, not a current per-token rate. The authors do argue it could be "several times higher" for larger models, citing Falcon-180B at 16 Wh under SLOs.

### 7.4 Versus Jegham (Claude-3.7 Sonnet, 100 in / 300 out)

The paper's own formula gives 5.0 mL. My bands give **LOW 0.14 / MID 1.1 / HIGH 5.2 mL**, so the HIGH band reproduces Jegham. That is by design, since Jegham's batch-8 assumption and 5.11 L/kWh EWIF sit at the conservative end.

### 7.5 Versus Mistral's 45 mL per 400-token response

MID gives **~1.5 mL**. The ~30× gap reflects:
- LCA scope: Water Consumption Potential including upstream, manufacturing and infrastructure
- A "marginal" figure that still bundles infrastructure
- Unknown energy per response and location

The per-response figure also seems high relative to the energy implied by 1.14 gCO2e. On a low-carbon (e.g. French) grid, 1.14 g would imply several Wh. Without Mistral's energy number this cannot be reconciled. **Do not mix LCA figures with operational coefficients.**

---

## 8. Relatable comparisons for status-line display

| Unit | Volume | Source |
|---|---|---|
| One drop | 0.05 mL | Google Gemini paper ("standard 0.05 mL drop") [V] |
| Teaspoon (US) | 4.93 mL | Standard unit. Altman's "one fifteenth of a teaspoon" [V] |
| Tablespoon (US) | 14.8 mL | Standard unit |
| Shot glass (1.5 fl oz) | 44 mL | Standard unit |
| **Glass of water (8 fl oz)** | **237 mL** | Standard unit |
| Bottle of water | 500 mL | Li et al.'s framing [V] |
| **Toilet flush, current federal max** | **1.6 gal = 6.06 L** | EPA WaterSense / EPAct 1992 [V] |
| Toilet flush, WaterSense | 1.28 gal = 4.85 L | EPA WaterSense [V] |
| Shower, per minute | 2.5 gal = 9.46 L (standard head); 2.0 gal WaterSense | EPA WaterSense [V] |
| Avg American's daily home use | 82 gal ≈ 310 L | EPA WaterSense (USGS 2015) [V] |
| Cup of coffee (125 mL), full supply chain | 140 L | Hoekstra 2008, *Water Footprint of Food* [V] |
| Glass of milk (250 mL), supply chain | 250 L | Hoekstra 2008 [V] |
| Beef, per kg | 15,500 L (15,400 in Mekonnen & Hoekstra 2012) | Hoekstra 2008 [V]; Mekonnen & Hoekstra [S] |
| 150 g hamburger patty | ≈ 2,300 L **[D]** (0.15 × 15,500) | Derived |
| One California almond | ~12 L (3.2 gal) per peer-reviewed estimate; 1.1 gal (4.2 L) per Almond Board | *Ecological Indicators* study [S]; Almond Board [S] |

**Caveat for food comparisons.** Food water footprints are *total* footprints (green rainwater + blue irrigation + grey dilution). AI water is *blue consumption*, so the comparison flatters AI. **For the status line, prefer blue-water comparisons**: drops, teaspoons, glasses, toilet flushes and shower-seconds. If food is shown, label it as "supply-chain water footprint".

Suggested display ladder:
- < 5 mL: drops
- < 250 mL: teaspoons or tablespoons
- < 6 L: glasses
- < 100 L: toilet flushes
- Above that: showers or "days of home water use"

At MID, the reference session (~390 mL) is ~1.7 glasses. A heavy week at Hausfather-scale usage (~47 L/week at MID) is ~8 toilet flushes.

---

## 9. Caveats and open uncertainties

1. **No Anthropic disclosure.** Every Claude-specific number is inferred from pricing, API throughput or open-model proxies. Model sizes, hardware (Trainium2 vs TPU vs GPU), batch sizes, utilization and locations are unknown.
2. **Energy per token spans about 10×** (0.3–3 Wh per 1K output). Batch size and hardware generation dominate: the ML.ENERGY data shows a 10–20× swing from batch 8 to batch 256+. Idle capacity (Google: +10%) and host overhead (+25%) matter too.
3. **Input vs cache economics are the least-evidenced part.** No public measurement exists of the energy of a prompt-cache hit in a production frontier system. The 0.1× figure is a pricing proxy, and pricing now varies by model (0.1× / 0.05× / 0.025×).
4. **Context-length dependence.** Per-token cost rises with context (attention over the KV cache). Flat per-token coefficients assume agentic-typical contexts of tens to hundreds of thousands of tokens.
5. **EWIF methodology dominates the water number.** Scope-2 is 75–90% of full-scope water. Hydro-evaporation allocation (LBNL 4.35–4.52 vs WRI 3.14) and location-based vs market-based accounting (PPAs) can move it 3× or more. Hourly variation is large too (Li Fig. 2: 1.5–3.0 L/kWh within a week in Virginia).
6. **Consumption ≠ impact.** A litre evaporated in Arizona matters more than one in Ireland. Water-stress-weighted metrics exist, e.g. arXiv 2506.22773 "Not All Water Consumption Is Equal" (not reviewed here in depth).
7. **On-site WUE trends.** Microsoft's zero-evaporation designs and liquid cooling cut on-site water but can raise PUE (and therefore scope-2 water). LBNL projects the average WUE *rising* to 0.45–0.48 L/kWh.
8. **Rapid efficiency change.** Google reports a 33× per-prompt energy drop in one year, and Oviedo sees 8–20× line-of-sight gains. Coefficients should carry a date and be revisited every ~6 months.
9. **Reasoning/thinking tokens** are billed as output tokens and are captured by the output coefficient. Hidden server-side work (routing, safety classifiers, tool orchestration, retries) is not visible to the client and is not included.
10. **Not verified in this pass:**
    - The Reig et al. (WRI 2020) EWIF values were taken via Li et al.
    - The Patterson and Wu fleet splits came from search summaries.
    - The almond study's authors and year were not confirmed.
    - The Jegham paper's peer-review status was not confirmed.
    - The Mistral "91%" water share came via The Batch.
    - AWS 2024 WUE 0.15 came via news summaries; the 2025 value of 0.12 is verified.

---

## 10. References

1. Li, P., Yang, J., Islam, M. A., Ren, S. "Making AI Less 'Thirsty'." *Communications of the ACM* 68(7), 2025. https://doi.org/10.1145/3724499. arXiv:2304.03271v5: https://arxiv.org/abs/2304.03271
2. Elsworth, C., Huang, K., Patterson, D., et al. (Google). "Measuring the environmental impact of delivering AI at Google Scale." arXiv:2508.15734, Aug 2025. https://arxiv.org/abs/2508.15734
3. Jegham, N., Abdelatti, M., Koh, C. Y., Elmoubarki, L., Hendawi, A. "How Hungry is AI? Benchmarking Energy, Water, and Carbon Footprint of LLM Inference." arXiv:2505.09598v6, Nov 2025. https://arxiv.org/abs/2505.09598
4. Luccioni, A. S., Jernite, Y., Strubell, E. "Power Hungry Processing: Watts Driving the Cost of AI Deployment?" ACM FAccT '24. arXiv:2311.16863. https://arxiv.org/abs/2311.16863
5. Altman, S. "The Gentle Singularity." June 2025. https://blog.samaltman.com/the-gentle-singularity
6. You, J. "How much energy does ChatGPT use?" Epoch AI Gradient Updates, Feb 7 2025. https://epoch.ai/gradient-updates/how-much-energy-does-chatgpt-use
7. Mistral AI. "Our contribution to a global environmental standard for AI." July 22 2025. https://mistral.ai/news/our-contribution-to-a-global-environmental-standard-for-ai. Summary: https://www.deeplearning.ai/the-batch/french-ai-startup-discloses-full-lifecycle-consumption-and-emissions-for-mistral-large-2
8. Chung, J.-W., et al. "The ML.ENERGY Benchmark: Toward Automated Inference Energy Measurement and Optimization." NeurIPS 2025 Datasets & Benchmarks. arXiv:2505.06371. https://arxiv.org/abs/2505.06371. Leaderboard v3.0 data: https://github.com/ml-energy/leaderboard (public/data/models). Blog: https://ml.energy/blog/measurement/energy/diagnosing-inference-energy-consumption-with-the-mlenergy-leaderboard-v30/
9. Oviedo, F., et al. (Microsoft). "Energy use of AI inference, efficiency pathways, and test-time scaling." *Joule*, 2026. https://www.cell.com/joule/fulltext/S2542-4351(26)00114-5. arXiv:2509.20241: https://arxiv.org/abs/2509.20241
10. Ruf, B., Detyniecki, M. "The Cost of Context: Profiling the Energy Footprint of Input Tokens in Large Language Models." HotCarbon 2026. https://hotcarbon.org/assets/2026/paper-17.pdf
11. Vellaisamy, P., Lam, V., Blanton, S., Shen, J. P. "Characterization of Request and Token Energy Costs for LLM Inference Workloads on GPU Platforms." IEEE IISWC 2026 (accepted). arXiv:2608.28044. https://arxiv.org/abs/2608.28044
12. Morrison, J., Na, C., Fernandez, J., Dettmers, T., Strubell, E., Dodge, J. "Holistically Evaluating the Environmental Impact of Creating Language Models." ICLR 2025. arXiv:2503.05804. https://arxiv.org/abs/2503.05804
13. Shehabi, A., et al. "2024 United States Data Center Energy Usage Report." Lawrence Berkeley National Laboratory, Dec 2024. https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf
14. Reig, P., Luo, T., Christensen, E., Sinistore, J. "Guidance for Calculating Water Use Embedded in Purchased Electricity." World Resources Institute, 2020. (Cited via Li et al.; not opened directly.)
15. Microsoft. "Measuring energy and water efficiency for Microsoft datacenters." https://datacenters.microsoft.com/sustainability/efficiency/. Zero-water design: https://www.microsoft.com/en-us/microsoft-cloud/blog/2024/12/09/sustainable-by-design-next-generation-datacenters-consume-zero-water-for-cooling/
16. Amazon. "AWS Cloud – Amazon Sustainability." https://sustainability.aboutamazon.com/products-services/aws-cloud
17. Google. "Operating sustainably – Google Data Centers." https://datacenters.google/operating-sustainably/
18. Couch, S. P. "Electricity use of AI coding agents." Jan 20 2026. https://simonpcouch.com/blog/2026-01-20-cc-impact/
19. Hausfather, Z. "The real energy use of agentic AI." The Climate Brink, 2026. https://www.theclimatebrink.com/p/the-real-energy-use-of-agentic-ai
20. Epoch AI. "What did it take to train Grok 4?" https://epoch.ai/data-insights/grok-4-training-resources
21. Patterson, D., et al. "The Carbon Footprint of Machine Learning Training Will Plateau, Then Shrink." *IEEE Computer*, 2022. https://arxiv.org/abs/2204.05149
22. Wu, C.-J., et al. "Sustainable AI: Environmental Implications, Challenges and Opportunities." MLSys 2022. https://arxiv.org/abs/2111.00364
23. Anthropic. "Pricing." Claude Platform docs (accessed 2026-09-27). https://platform.claude.com/docs/en/about-claude/pricing
24. CNBC, "Anthropic to spend $50 billion on U.S. AI infrastructure…", Nov 12 2025. https://www.cnbc.com/2025/11/12/anthropic-ai-data-centers-texas-new-york.html. DCD coverage: https://www.datacenterdynamics.com/en/news/anthropic-plans-50bn-us-data-center-spend-starting-with-fluidstack-sites-in-texas-and-new-york/
25. Hoekstra, A. Y. "The water footprint of food." 2008. https://www.waterfootprint.org/resources/Hoekstra-2008-WaterfootprintFood.pdf
26. Mekonnen, M. M., Hoekstra, A. Y. "A Global Assessment of the Water Footprint of Farm Animal Products." *Ecosystems*, 2012. https://link.springer.com/article/10.1007/s10021-011-9517-8
27. "Water-indexed benefits and impacts of California almonds." *Ecological Indicators*. https://www.sciencedirect.com/science/article/pii/S1470160X17308592
28. US EPA WaterSense: statistics (https://www.epa.gov/watersense/statistics-and-facts), residential toilets (https://www.epa.gov/watersense/residential-toilets), showerheads (https://www.epa.gov/watersense/showerheads)
29. Network World, "Amazon claims its data centers are 7x more water-efficient than the industry average," June 11 2026. https://www.networkworld.com/article/4184250/amazon-claims-its-data-centers-are-7x-more-water-efficient-than-the-industry-average.html
30. (Secondary, not relied on) mdodkins, "Claude Code Energy Use Estimate," Mar 2026. https://gist.github.com/mdodkins/9b49624855cc41570c9d1012e0d5d157

# NERV API Cost Ceiling Analysis
> Created: 2026-02-25
> Status: **LOCKED — Critical Business Intelligence**

## Summary

At $3,500/mo per project revenue, API costs are negligible at any realistic usage level and still profitable even at absurd 100x abuse scenarios. **The pricing model is bulletproof.**

## Assumptions (Baseline = 1x)

| Parameter | Value |
|---|---|
| Queries/project/day | 30 |
| Tokens/query (in/out) | 800/400 |
| Reports/project/day | 3 (~2,000 tok each) |
| File classifications/project/day | 20 (20% need AI) |
| Revenue/project/month | $3,500 |
| Hardware cost (one-time) | ~$1,720 (covered by $15K setup) |

## Cost Per Project Per Month — All Scenarios

### Worst Case: Claude Sonnet 4 (most expensive model, all traffic)

| Usage | Queries/Day | Cost/Project/Mo | Margin $ | Margin % |
|:---:|:---:|:---:|:---:|:---:|
| 1x | 30 | $10.63 | $3,489.37 | 99.7% |
| 2x | 60 | $21.26 | $3,478.74 | 99.4% |
| 3x | 90 | $31.89 | $3,468.11 | 99.1% |
| 5x | 150 | $53.15 | $3,446.85 | 98.5% |
| 10x | 300 | $106.30 | $3,393.70 | 97.0% |
| **100x** | **3,000** | **$1,062.96** | **$2,437.04** | **69.6%** |

### Cheapest Cloud: GPT-4o-mini

| Usage | Queries/Day | Cost/Project/Mo | Margin $ | Margin % |
|:---:|:---:|:---:|:---:|:---:|
| 1x | 30 | $0.45 | $3,499.55 | 100.0% |
| 2x | 60 | $0.90 | $3,499.10 | 100.0% |
| 3x | 90 | $1.35 | $3,498.65 | 100.0% |
| 5x | 150 | $2.24 | $3,497.76 | 99.9% |
| 10x | 300 | $4.48 | $3,495.52 | 99.9% |
| **100x** | **3,000** | **$44.84** | **$3,455.16** | **98.7%** |

### Smart Route: Expensive model for user queries, cheap/local for bulk

| Usage | Queries/Day | Cost/Project/Mo | Margin $ | Margin % |
|:---:|:---:|:---:|:---:|:---:|
| 1x | 30 | $5.48 | $3,494.52 | 99.8% |
| 2x | 60 | $10.96 | $3,489.04 | 99.7% |
| 3x | 90 | $16.44 | $3,483.56 | 99.5% |
| 5x | 150 | $27.40 | $3,472.60 | 99.2% |
| 10x | 300 | $54.79 | $3,445.21 | 98.4% |
| **100x** | **3,000** | **$547.92** | **$2,952.08** | **84.3%** |

## 100x Context — "Trailer Life" Stress Test

100x = 3,000 queries per project per day = one query every 29 seconds, 24 hours straight. This models extreme early adoption behavior: field guys testing limits, pranking each other, using it for non-work tasks. Even at this level:

- **Worst case (Sonnet 4 everything): 69.6% margin — still profitable**
- **Smart routing: 84.3% margin**
- **Cheap model: 98.7% margin**

Key insight: casual/abuse queries don't need the expensive model. Smart routing automatically sends simple stuff to Haiku/4o-mini and reserves the big model for real PM work. This is the natural defense against abuse without rate limiting.

## All Models at 100x (Full Detail)

| Model | Cost/Project/Mo | Margin % |
|:---:|:---:|:---:|
| Claude Sonnet 4 | $1,062.96 | 69.6% |
| GPT-4o | $747.30 | 78.6% |
| Smart Route (4o + local) | $547.92 | 84.3% |
| Claude Haiku 3.5 | $283.46 | 91.9% |
| GPT-4o-mini | $44.84 | 98.7% |
| Local (Ollama) | $0.00 | 100.0% |

## Pricing Model Tiers (for reference)

| Provider/Model | Input $/1M tok | Output $/1M tok |
|---|---|---|
| OpenAI GPT-4o | $2.50 | $10.00 |
| OpenAI GPT-4o-mini | $0.15 | $0.60 |
| Anthropic Claude Sonnet 4 | $3.00 | $15.00 |
| Anthropic Claude Haiku 3.5 | $0.80 | $4.00 |
| Local (Ollama) | $0.00 | $0.00 |

## Key Business Takeaways

1. **API costs will never kill this business model.** Even worst-case-on-worst-case is profitable.
2. **Smart routing is free margin insurance.** Route casual queries to cheap models automatically.
3. **High usage = high adoption = easy renewals.** If they're abusing it, they can't live without it.
4. **The real cost is hardware ($1,720) and that's covered by the $15K setup fee with 89% margin.**
5. **This is a services business with software margins.**

## Safety Valves (Recommended)

- Per-user-role rate limits (field guys vs PMs vs execs)
- Smart model routing based on query complexity
- Usage dashboard in NERV interface (transparency builds trust)
- Monthly usage reports to client (shows value, justifies renewal)

---

## Caveat Analysis (mini-Moby Review, 2026-02-25)

mini-Moby fact-checked the base model and confirmed math is internally consistent. Raised 6 caveats that could increase real-world spend. Here's the honest assessment:

### Caveat 1: Higher tokens/query (long docs, long chats, large context)
**Risk: MODERATE**
A PM pasting a 50-page spec into chat could hit 4,000-8,000 input tokens instead of 800. However, most field queries are short ("what's the status of RFI-42?" / "when is the concrete pour?"). Heavy-context queries are maybe 10-15% of volume.

**Adjustment:** Model a "heavy" scenario at 3x token size (2,400 in / 1,200 out) for 15% of queries.
- Impact at 1x usage: ~$15-16/project/mo on Sonnet 4 (vs $10.63 base) — still negligible
- Impact at 100x: ~$1,500/project/mo on Sonnet 4 — still 57% margin

### Caveat 2: Anthropic long-context premium (>200K input)
**Risk: NEGLIGIBLE**
NERV uses vector search (embedding pipeline) to retrieve relevant chunks. We never stuff raw documents into context. A typical query hits the index, pulls 5-10 chunks (~2,000 tokens), and sends that with the question. We will never approach 200K context windows in normal operation.

### Caveat 3: Retries/failovers (duplicate token burn)
**Risk: LOW**
OpenClaw handles backoff and rotation. Realistic overhead: 5-10% on failed requests. At base cost levels this is pennies.

**Adjustment:** Apply 10% retry overhead to all scenarios as safety margin.

### Caveat 4: Web search/tool fixed token blocks
**Risk: LOW for construction PM**
EVAs primarily query internal NERV data (project docs, emails, submittals). Web search is not a core workflow. If added for material pricing lookups or code research, it's low-frequency and can use cheap models.

### Caveat 5: Embeddings/OCR/background jobs
**Risk: LOW (mostly local)**
- **Embeddings:** Run locally on all-MiniLM-L6-v2. Zero API cost.
- **OCR:** One-time ingest cost per document. If using cloud OCR (e.g., GPT-4o vision for scanned drawings), estimate ~$0.01-0.05 per page. A 15TB onboarding with 50K pages of scanned docs = ~$500-2,500 one-time. Covered by $15K setup fee.
- **Background jobs:** Scheduled reports already modeled. Webhook processing is structured data parsing, no AI needed.

### Caveat 6: Image/audio models
**Risk: MODERATE if enabled — but controllable**
Site photo analysis (progress photos, safety violations, punchlist documentation) would use vision models. GPT-4o vision: ~$0.003-0.01 per image depending on resolution.
- 50 site photos/day analyzed = ~$0.25-0.50/day = $7.50-15/project/mo
- This is a premium feature we can price separately or absorb within margin.

Audio (voice-to-text for field reports) would use Whisper or similar. Negligible cost (~$0.006/minute).

### Adjusted 3-Scenario Model

| Scenario | Description | Sonnet 4 Cost/Proj/Mo | Margin % |
|---|---|---|---|
| **Lean** | Base model as calculated (light usage, short queries) | $10.63 | 99.7% |
| **Realistic** | 3x queries, 15% heavy-context, 10% retry overhead, 20 photos/day, OCR amortized | ~$65-80 | 97.7-98.1% |
| **Heavy** | 10x queries, 25% heavy-context, 10% retry, 50 photos/day, full vision features | ~$200-250 | 92.9-94.3% |
| **Abuse (100x)** | Trailer life stress test + all caveats stacked | ~$1,800-2,000 | 42.9-48.6% |

### Revised Bottom Line

- **Base model is directionally correct and confirmed by independent review**
- **Realistic scenario: ~$65-80/project/mo on the most expensive model = 97-98% margin**
- **Even stacking ALL caveats at 100x abuse: still profitable at ~45% margin**
- **Smart routing + local embeddings + local models for bulk work = the caveats shrink dramatically**
- **Treat base tables as floor estimates, realistic scenario as planning number, heavy as stress test**

---

## Calculator

Tool: `nerv-deploy/tools/cost-calculator.py`
Run: `python3 cost-calculator.py --queries-per-day 300 --reports-per-day 30 --classifications-per-day 200`
Supports all parameter overrides via CLI args.

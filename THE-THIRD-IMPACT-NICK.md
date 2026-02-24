# THE THIRD IMPACT
## Your Copy — Evangelion Project Status Report
**February 18, 2026**

---

## What We Have

### The Product
AI agents for construction GCs, deployed on local mini-servers (NERV units). Integrated with Procore. Data never leaves the client's building.

- **EVA-00:** Project database & search — the anchor product
- **EVA-01:** Submittal management agent
- **EVA-02:** RFI & drawing analysis agent

### Pricing
- $2-3k setup (includes hardware)
- $3-5k/month per agent
- Still need: detailed cost breakdown for API costs per client

### What's Built
| Item | Status | Location on Moby-1 |
|------|--------|-------------------|
| Deployment template (Docker + config + scripts) | ✅ Done | `eva-agent/deployment-template/` |
| EVA-00 database schema (PostgreSQL + vector search) | ✅ Designed | `eva-agent/eva-00-design/` |
| Drawing analysis strategy (4-tier approach) | ✅ Designed | `eva-agent/drawing-analysis-design/` |
| NERV hardware spec (3 tiers) | ✅ Done | `eva-agent/NERV-HARDWARE.md` |
| Procore sandbox (554 users, 118 vendors) | ✅ Populated | Procore sandbox |
| DXF extraction pipeline | ✅ Validated | Tested on 14 1750 sheets |
| PDF extraction pipeline | ✅ Validated | PyMuPDF, $0 cost |
| Cover sheet parser | ✅ Proven | PyMuPDF link extraction |
| Drawing index pipeline | ✅ Working | `eva-drawing-index/` |

### What's NOT Built Yet
1. ❌ Running EVA-00 database (schema exists, not deployed)
2. ❌ EVA-01 submittal agent prototype
3. ❌ Batch cover sheet import tool
4. ❌ Client demo package
5. ❌ Pricing/cost model
6. ❌ First sales conversation

---

## The Big Technical Insight

**Text extraction beats AI vision for construction drawings.** This is the competitive moat.

- PyMuPDF reads PDFs → instant, free, 100% accurate
- ezdxf reads DXF/CAD files → instant, free, 100% accurate
- AI vision models → slow, expensive, and actually got wrong answers in our tests

Everyone else is throwing expensive AI at drawings. We extract structured data first, AI second. Thousands of files = minutes at $0.

---

## Procore API — The Gotchas

**Working:** Submittals, vendors, users, file upload, drawing revisions, RFIs
**Broken:** No spec section API, no submittal workflow management, no status changes, API-created users can't be submittal reviewers

**Key numbers:**
- Company ID: 4281379, Project ID: 316469
- Rate limit: 100 requests per 60 seconds
- Only 4 built-in users work as submittal participants

---

## Your Credentials (on Moby-1)

| Account | Details | Location |
|---------|---------|----------|
| GitHub | mechamoby | gh CLI auth'd |
| Gmail | mecha.moby@gmail.com | SMTP/IMAP configured |
| Procore Dev | Sandbox app | `.credentials/procore.env` |
| DocuSign Dev | Sandbox app "Moby" | `.credentials/docusign.env` |
| Web Terminal | http://192.168.8.124:7681 | moby / eva2026 |

---

## What To Tell The New AI

Point it at `THE-THIRD-IMPACT.md` on Moby-1. That file is written specifically for a ChatGPT-based successor — it has everything: business context, technical details, API quirks, mistakes to avoid, file locations, and next steps.

The AI handoff doc is ~17k words. It covers:
- Full business concept and pricing
- All Procore API knowledge (what works, what doesn't)
- Every file and where it lives
- 13 specific mistakes/lessons learned
- Priority-ordered next steps
- Nick's working style and security protocols

---

## Priority Next Steps

1. Get EVA-00 database running with real Procore data
2. Build EVA-01 submittal agent (first demo-able product)
3. Batch cover sheet parser for data migration
4. Client demo package
5. Pricing finalization
6. First sales conversation

---

*Created by Moby 🐋 as a contingency plan. All project knowledge preserved on Moby-1.*
*The AI-detailed version: `/home/moby/.openclaw/workspace/THE-THIRD-IMPACT.md`*
*This version: `/home/moby/.openclaw/workspace/THE-THIRD-IMPACT-NICK.md`*

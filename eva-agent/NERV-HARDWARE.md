# NERV Server Hardware Configuration

## Requirements
- Run OpenClaw + all EVA agents 24/7
- PostgreSQL 16 + pgvector (semantic search across thousands of docs)
- DWG→DXF conversion pipeline (ODA File Converter or LibreDWG)
- Local embedding model (nomic-embed-text via Ollama)
- Optional local LLM for sensitive queries (Llama 3, Mistral)
- Store 20+ projects worth of drawings, submittals, RFIs (500GB+)
- Redis caching layer
- Docker containerized everything
- Sits in client's main office, runs silent 24/7

## Option A: Mini PC (Recommended for Phase 1)
- **Platform:** Intel NUC 14 Pro+ or ASUS ExpertCenter PN65
- **CPU:** Intel Core Ultra 7 155H (16C/22T)
- **RAM:** 64GB DDR5-5600
- **Storage:** 2TB NVMe (OS/apps) + 4TB NVMe (data)
- **GPU:** None needed
- **Network:** 2.5GbE built-in
- **Cost:** ~$1,200-1,500
- **Best for:** Most clients, Phase 1, fits inside $2-3k setup fee

## Option B: Workstation Mini (GPU for local LLM)
- **Platform:** Minisforum MS-A1 or similar AMD AM5 mini
- **CPU:** AMD Ryzen 7 8700G or Ryzen 9 7940HS
- **RAM:** 64GB DDR5
- **Storage:** 2TB + 4TB NVMe
- **GPU:** NVIDIA RTX 4060 (8GB) or RTX 4070 (12GB)
- **Network:** 2.5GbE
- **Cost:** ~$2,000-2,500
- **Best for:** Air-gapped operation, heavy batch drawing processing, local LLM

## Option C: Enterprise-Grade (Large firms, 50+ users)
- **Platform:** Dell OptiPlex Micro or HP ProDesk Mini
- **CPU:** Intel Core Ultra 9 185H or i7-14700
- **RAM:** 96GB DDR5
- **Storage:** 2TB + 8TB NVMe
- **GPU:** Optional external via Thunderbolt
- **Cost:** ~$2,500-3,500
- **Best for:** Large GCs, IT department requirements, warranty support

## Software Stack
```
Docker Compose:
├── openclaw          (EVA agent runtime)
├── postgresql-16     (pgvector, full-text search, all project data)
├── redis-7           (caching, session management, job queues)
├── ollama            (local embeddings, optional local LLM)
├── oda-converter     (DWG→DXF conversion service)
├── nginx             (reverse proxy, TLS for VPN access)
└── backup-service    (nightly encrypted backups to USB/NAS)
```

## DWG Pipeline
1. ODA File Converter runs headless on Linux as Docker service
2. DWG drops in → auto-converts to DXF → ezdxf parses → data to PostgreSQL
3. ~2-5 seconds per DWG file
4. Moby-1 failed because compiling LibreDWG hit memory limits; NERV with 64GB = non-issue

## Network/Remote Access
- WireGuard VPN or Cloudflare Tunnel for zero-config remote access
- Field users connect via phone/tablet
- EVA agents accessible via Telegram, email, or web interface

## Pricing Impact
- Hardware: $1,200-1,500 (included in $2-3k setup fee)
- Setup time: 2-4 hours (included)
- Monthly: hosting + API costs ~$200-400/mo → client pays $3-5k/mo per agent
- **TODO: Detailed cost breakdown needed for hosting + API costs and monthly agent pricing**

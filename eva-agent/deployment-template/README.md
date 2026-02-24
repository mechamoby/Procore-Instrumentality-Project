# EVA — Construction AI Agent Deployment Template

> **Evangelion Project (EVA)** — AI agents for general contractors and developers.
> Each client gets a dedicated, locally-deployed agent. Data never leaves their building.

## What This Is

A clone-and-configure template for deploying a new EVA agent instance to a construction company client. No code changes required — all customization happens through config files and prompt templates.

**Target deployment time: under 30 minutes** from clone to go-live.

## Architecture

```
┌─────────────────────────────────────┐
│         Client's Mini-Server        │
│                                     │
│  ┌───────────┐  ┌───────────────┐   │
│  │  OpenClaw  │──│  PostgreSQL   │   │
│  │  (Agent)   │  │  (Data Store) │   │
│  └─────┬─────┘  └───────────────┘   │
│        │         ┌───────────────┐   │
│        └─────────│    Redis      │   │
│                  │  (Sessions)   │   │
│                  └───────────────┘   │
└──────────┬──────────────────────────┘
           │ Outbound only
     ┌─────┴─────┐
     │  Procore   │
     │  DocuSign  │
     │  Email     │
     └───────────┘
```

## Quick Start

```bash
# 1. Clone template for new client
cp -r deployment-template/ clients/acme-construction/
cd clients/acme-construction/

# 2. Run interactive setup (collects company info, creds, users)
chmod +x scripts/setup.sh scripts/deploy.sh
./scripts/setup.sh

# 3. Deploy
./scripts/deploy.sh

# 4. Verify
curl http://localhost:3000/health
```

## File Structure

```
deployment-template/
├── README.md                    # This file
├── docker-compose.yml           # Production compose stack
├── .env.example                 # Environment variables template
├── config/
│   ├── agent-config.yaml        # Main agent configuration
│   ├── roles.yaml               # RBAC definitions
│   └── prompts/
│       ├── base-system.md       # Core construction agent prompt
│       ├── daily-reports.md     # Daily report workflow prompt
│       └── submittals.md        # Submittal tracking prompt
├── scripts/
│   ├── setup.sh                 # Interactive client onboarding
│   └── deploy.sh                # One-command deployment
└── docs/
    ├── CLIENT-ONBOARDING.md     # Full onboarding checklist
    └── MULTI-AGENT-OPTION-B.md  # Katsuragi + EVA sub-agent deployment pattern
```

## Configuration Overview

| File | What to customize | When |
|------|------------------|------|
| `config/agent-config.yaml` | Company name, integrations, users | During setup.sh |
| `config/roles.yaml` | Permission scopes (rarely changed) | Only if client needs custom roles |
| `config/prompts/base-system.md` | Agent personality, domain focus | Only for specialized clients |
| `.env` | API keys, secrets | During setup.sh |

## Requirements

- Docker Engine 24+ and Docker Compose v2
- 8GB RAM minimum (16GB recommended)
- 50GB disk (SSD preferred)
- Outbound HTTPS access to Procore, DocuSign, and SMTP
- Static LAN IP for the mini-server

## Support

EVA is built and maintained by the Evangelion Project team.
Contact: [your-support-email]

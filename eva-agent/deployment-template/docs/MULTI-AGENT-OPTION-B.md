# Multi-Agent Deployment (Option B)

This template supports **Option B** from Third Impact Section 11:
- **One client-facing coordinator** (Katsuragi)
- **Multiple specialist EVA sub-agents** behind the scenes

## Goal
Keep one simple Telegram entrypoint for client users while preserving specialist agent isolation.

## Recommended Agent Topology
- `katsuragi` (default/client-facing)
- `eva-00` (project historian, DB/query)
- `eva-01` (submittals)
- `eva-02` (RFIs)

## OpenClaw Config Skeleton

```json5
{
  "agents": {
    "list": [
      { "id": "katsuragi", "workspace": "~/workspace-katsuragi", "default": true, "model": "openai-codex/gpt-5.3-codex" },
      { "id": "eva-00", "workspace": "~/workspace-eva-00", "model": "openai-codex/gpt-5.3-codex" },
      { "id": "eva-01", "workspace": "~/workspace-eva-01", "model": "openai-codex/gpt-5.3-codex" },
      { "id": "eva-02", "workspace": "~/workspace-eva-02", "model": "openai-codex/gpt-5.3-codex" }
    ]
  },
  "bindings": [
    { "agentId": "katsuragi", "match": { "channel": "telegram", "accountId": "default" } }
  ]
}
```

## Routing Rules
1. **All external user chat enters Katsuragi only**.
2. Katsuragi delegates work via `sessions_spawn` / `sessions_send`.
3. EVA agents do not directly answer end users.
4. Katsuragi returns final response after collecting specialist output.

## Session Isolation
- Each user DM thread remains isolated in its own session key.
- Sub-agent calls should stay within that user’s session tree.

## Operational Notes
- Keep all agents on the same auth provider for predictable billing.
- Use per-agent workspace files (`SOUL.md`, `AGENTS.md`, `USER.md`) for role boundaries.
- Restrict channel bindings so EVA-* are never directly exposed.

## First-Pass Acceptance Checklist
- [ ] Katsuragi receives Telegram messages successfully
- [ ] Katsuragi can spawn EVA-00/01/02
- [ ] EVA responses flow back to Katsuragi and then to user
- [ ] No direct channel binding for EVA agents
- [ ] Session handoff validated with two concurrent users

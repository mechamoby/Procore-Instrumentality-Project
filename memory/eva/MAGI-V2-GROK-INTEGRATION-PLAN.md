# Operation MAGI v2 — Grok Integration (High Priority)

## Objective
Upgrade MAGI into a hybrid research system:
- **MAGI-Core (deterministic)**: technical synthesis + final authority
- **MAGI-Culture Lens (Grok)**: construction culture/philosophy realism + adversarial critique
- **MAGI-Verifier (deterministic)**: fact-check + merge gate

## Constraints discovered on this host
- Current configured model inventory: `openai-codex/gpt-5.3-codex` only.
- OpenClaw docs indicate xAI provider auth is currently API-key based (`XAI_API_KEY`).
- No confirmed subscription OAuth flow for xAI/Grok in current OpenClaw build.

## What can be built immediately (done now)
1. MAGI v2 architecture + workflow definition (this doc)
2. Preflight script to verify Grok provider/model presence
3. Runtime test protocol for culture pipeline quality

## Activation requirements (to go live)
1. xAI provider credentials available to gateway host (or OpenRouter model route)
2. Grok model visible in `openclaw models list`
3. Agent model routing updated (Magi core + Grok culture lane)
4. Smoke tests pass (prompt fidelity + verifier gate)

## Quality gate (must pass)
- Culture output must include:
  - field language realism
  - role-specific psychology (PM/super/executive/sub)
  - practical conflict patterns and mitigations
- Verifier must reject unsupported factual claims.

## Initial execution sequence
1. Run `scripts/magi-v2-preflight.sh`
2. If provider unavailable, block with explicit action needed
3. Once available, route MAGI-Culture Lens tasks to Grok model
4. Keep MAGI-Core final synthesis on deterministic model
5. Validate with 5 benchmark prompts and compare against prior culture docs

## Benchmark prompts (v1)
1. "Give me the 8 most common PM-vs-super breakdowns on multifamily projects and how each actually sounds in the field."
2. "Rewrite this polished executive update in real South Florida GC language without losing meaning."
3. "Simulate a hostile OAC meeting where submittals are late and generate de-escalation tactics by role."
4. "List culture pitfalls that kill AI adoption on site and how to neutralize each in rollout order."
5. "Critique our EVA value prop like a skeptical GC owner, then produce rebuttals."

# MAGI v2 — What I need from Nick to make Grok operational

## Required now (minimum)
1. Confirm which path you want:
   - A) xAI direct provider in OpenClaw
   - B) OpenRouter route to Grok model
2. Provide credential method supported by current OpenClaw runtime on host:
   - currently expected: API key/token path (not confirmed subscription OAuth flow for xAI)

## Important constraint
Your requirement is "use Grok subscription OAuth token (no extra API fees)."
- In current OpenClaw build on this host, I cannot find a verified xAI subscription OAuth login flow equivalent to `openai-codex`.
- I can proceed instantly once such a supported auth path exists here.

## Once credentials are available
I will complete:
- provider auth setup
- model routing config for MAGI v2 lanes
- smoke test execution
- benchmark quality report vs existing culture docs

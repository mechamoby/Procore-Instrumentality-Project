# NERV ↔ Telegram Sync Runbook

## Baseline
- Ensure explicit main binding exists when any custom bindings are used:
  - `{agentId:"main", match:{channel:"telegram", accountId:"default"}}`
- Keep Katsuragi and main bot bindings explicit.

## Health Check
```bash
scripts/check-telegram-sync.sh
```

## Smoke Test
1. Send Telegram DM to @MechaMobyBot
2. Confirm inbound appears in NERV activity feed
3. Send response from NERV; confirm Telegram delivery
4. Repeat on @KatsuragiOD_Bot

## If Broken
1. `openclaw gateway status`
2. verify bindings in `~/.openclaw/openclaw.json`
3. restart gateway only from terminal context, not Telegram session
4. inspect logs for `telegram getFile`/polling errors

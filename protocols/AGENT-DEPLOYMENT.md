# NERV Agent Deployment Protocol
> Created: 2026-02-26
> Status: LOCKED — follow exactly, learned the hard way
> Time to deploy: ~15 minutes when done right

---

## Prerequisites (from client)
1. **Client's name** (the human, not the bot)
2. **Bot name** (what the agent calls itself)
3. **OpenAI account email + password** (for OAuth token)
4. **Business details** (what they do, what they need help with)
5. **Telegram** installed on their phone

---

## Step 1: Create Telegram Bot (~2 min)

On client's phone (or BotFather from any Telegram):
1. Open Telegram → search `@BotFather` → Start
2. Send `/newbot`
3. **Display name:** the bot name (e.g., "Almudena")
4. **Username:** must end in `bot` (e.g., `AlmudenaBot`)
5. Copy the **bot token** (format: `1234567890:AAH...`)

---

## Step 2: Create Agent Config (~3 min)

### 2a. Create directories
```bash
mkdir -p ~/.openclaw/agents/<agent-id>/agent
mkdir -p ~/.openclaw/workspace-<agent-id>
```

### 2b. Write IDENTITY.md (workspace)
```markdown
# IDENTITY.md
- **Name:** <bot-name>
- **Creature:** AI business assistant
- **Vibe:** <personality summary>
- **Emoji:** <emoji>
```

### 2c. Write SOUL.md (workspace + agent dir — MUST be identical copies)
Key rules:
- First line must state: "I'm **<bot-name>**"
- Explicitly state the USER's name (the human)
- Define tone clearly (direct? warm? formal?)
- List what NOT to do (fluff, fake enthusiasm, etc.)
- Copy to BOTH locations:
  - `~/.openclaw/workspace-<agent-id>/SOUL.md`
  - `~/.openclaw/agents/<agent-id>/agent/SOUL.md`

### 2d. Write USER.md (workspace)
- Header: `# USER.md — About <client-name>`
- Name, business, location, language preferences
- **Personality notes** (direct? casual? formal? hates fluff?)
- Tech comfort level
- What they need help with

### 2e. Write AGENTS.md (workspace — THIS IS CRITICAL)
**Must include identity rules at the TOP:**
```markdown
## CRITICAL IDENTITY RULES
- **Your name is <bot-name>.** NEVER call yourself <agent-id> or anything else.
- **The user's name is <client-name>.** Always call them <client-name>.
- <bot-name> = you (the bot). <client-name> = them (the human).
```

⚠️ **LESSON LEARNED:** The workspace AGENTS.md is loaded by the runtime. The agent dir AGENTS.md is NOT the one that matters for identity. Always put identity rules in the WORKSPACE AGENTS.md.

---

## Step 3: OpenAI OAuth Token (~3 min)

### 3a. Log into ChatGPT via browser automation
```
1. Open browser to https://chatgpt.com/auth/login
2. Click "Log in"
3. Enter client's email + password
4. Complete any 2FA if needed
5. Once logged in, navigate to: https://chatgpt.com/api/auth/session
6. Extract the "accessToken" value — MUST start with "eyJ" (it's a JWT)
```

### 3b. Save the token
```bash
openclaw models auth paste-token --provider openai-codex --agent <agent-id> --expires-in 10d
# Paste the eyJ... token when prompted
```

### 3c. VERIFY the token was saved correctly
```bash
python3 -c "
import json
with open('/home/moby/.openclaw/agents/<agent-id>/agent/auth-profiles.json') as f:
    d = json.load(f)
p = d['profiles']['openai-codex:default']
print(f'Is JWT: {p[\"access\"].startswith(\"eyJ\")}')
print(f'Has anthropic fallback: {\"anthropic:default\" in d[\"profiles\"]}')
"
```

⚠️ **CRITICAL CHECKS:**
- Token MUST start with `eyJ` — if it starts with anything else, it's the WRONG token
- There should be NO `anthropic:default` profile (prevents silent fallback to our key)
- If `paste-token` doesn't overwrite, write the file directly with Python

### 3d. If paste-token doesn't work, write directly:
```python
auth_profiles = {
    "version": 1,
    "profiles": {
        "openai-codex:default": {
            "type": "oauth",
            "provider": "openai-codex",
            "access": "<JWT_TOKEN>",
            "refresh": "",
            "expires": <epoch_ms_10_days_from_now>
        }
    },
    "lastGood": {
        "openai-codex": "openai-codex:default"
    }
}
```

---

## Step 4: Register in openclaw.json (~2 min)

### 4a. Add agent to agents list
```json
{
    "id": "<agent-id>",
    "name": "<Bot Name>",
    "workspace": "/home/moby/.openclaw/workspace-<agent-id>",
    "agentDir": "/home/moby/.openclaw/agents/<agent-id>/agent",
    "model": "openai-codex/gpt-5.3-codex"
}
```

⚠️ **Model string must be exactly:** `openai-codex/gpt-5.3-codex`
- NOT `openai-codex:<agent-id>/gpt-5`
- NOT `openai-codex/gpt-5`

### 4b. Add Telegram account
```json
"<agent-id>": {
    "enabled": true,
    "dmPolicy": "allowlist",
    "botToken": "<bot-token-from-botfather>",
    "allowFrom": ["<client-chat-id>"],
    "groupPolicy": "allowlist",
    "streaming": true
}
```

### 4c. Add binding (⚠️ MANDATORY — without this, messages route to main agent)
```json
{
    "agentId": "<agent-id>",
    "match": {
        "channel": "telegram",
        "accountId": "<agent-id>"
    }
}
```

### 4d. (Optional) Add to main agent's subagent allowlist

---

## Step 5: Get Client's Chat ID (~1 min)

1. Temporarily set `"dmPolicy": "pairing"` in telegram account config
2. Have client message the bot (anything — "hello")
3. They'll see a pairing code
4. Run: `openclaw pairing approve telegram <code>`
5. Note their chat ID from the pairing message
6. Switch back to `"dmPolicy": "allowlist"` with their chat ID in `allowFrom`

---

## Step 6: Verify (~2 min)

```bash
# 1. Gateway picks up config
openclaw gateway status

# 2. No sessions cached
ls ~/.openclaw/agents/<agent-id>/sessions/

# 3. Auth profile is correct
python3 -c "
import json
with open('$HOME/.openclaw/agents/<agent-id>/agent/auth-profiles.json') as f:
    d = json.load(f)
print('JWT:', d['profiles']['openai-codex:default']['access'][:10])
print('No fallback:', 'anthropic:default' not in d['profiles'])
"

# 4. Have client send a test message
# 5. Confirm correct name, correct tone, correct model
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bot calls user wrong name | AGENTS.md missing identity rules | Add CRITICAL IDENTITY RULES to workspace AGENTS.md |
| Bot calls itself wrong name | SOUL.md not updated or cached session | Update SOUL.md in BOTH locations, nuke sessions |
| "Failed to extract accountId" | Wrong token format (session cookie vs JWT) | Re-extract token from /api/auth/session — must start with `eyJ` |
| Falls back to Opus/our key | anthropic:default in auth-profiles.json | Remove anthropic profile, leave only openai-codex |
| Messages go to main agent | Missing binding in openclaw.json | Add bindings[] entry with agentId + channel/accountId match |
| Old personality persists | Cached session | `rm -rf ~/.openclaw/agents/<agent-id>/sessions/*` |
| Config rejected on reload | Invalid key in config | Check gateway logs, remove invalid keys |

---

## Token Refresh (every ~10 days)

ChatGPT session tokens expire. To refresh:
1. Log into ChatGPT with client credentials (browser or automation)
2. Navigate to `https://chatgpt.com/api/auth/session`
3. Extract new JWT accessToken
4. Run `openclaw models auth paste-token --provider openai-codex --agent <agent-id> --expires-in 10d`
5. Verify token starts with `eyJ`

**TODO:** Automate this with refresh token flow if available.

---

## Checklist (copy for each deployment)

- [ ] Telegram bot created via BotFather
- [ ] Directories created (agents + workspace)
- [ ] IDENTITY.md written
- [ ] SOUL.md written (BOTH copies match)
- [ ] USER.md written
- [ ] AGENTS.md written with identity rules at TOP
- [ ] OAuth JWT token saved (starts with `eyJ`, no anthropic fallback)
- [ ] Agent added to openclaw.json agents list
- [ ] Model set to `openai-codex/gpt-5.3-codex`
- [ ] Telegram account added with bot token
- [ ] Binding added in bindings[]
- [ ] Client paired and chat ID in allowFrom
- [ ] dmPolicy switched to allowlist
- [ ] Sessions directory empty
- [ ] Gateway restarted/reloaded
- [ ] Test message confirms correct name + tone + model

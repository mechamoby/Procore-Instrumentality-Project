#!/bin/bash
# Katsuragi email poller — runs every minute via cron
LOCKFILE="/tmp/katsuragi-email-poll.lock"

if [ -f "$LOCKFILE" ]; then
    LOCKPID=$(cat "$LOCKFILE")
    if kill -0 "$LOCKPID" 2>/dev/null; then
        exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

cd /home/moby/.openclaw/workspace

# Source env if needed
export OPENCLAW_GATEWAY_PORT=${OPENCLAW_GATEWAY_PORT:-18789}
export OPENCLAW_GATEWAY_TOKEN=${OPENCLAW_GATEWAY_TOKEN:-$(cat /home/moby/.openclaw/.gateway-token 2>/dev/null)}

RESULT=$(python3 scripts/katsuragi-email.py poll 2>/dev/null)
NEW=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('new_emails',0))" 2>/dev/null)

if [ "$NEW" != "0" ] && [ -n "$NEW" ]; then
    echo "$(date): $NEW new email(s)" >> /tmp/katsuragi-email.log
    
    # Trigger Katsuragi via openclaw agent
    /home/moby/.npm-global/bin/openclaw agent --agent katsuragi --channel telegram \
        -m "New submittal email received. Check your INBOX.md and process it." \
        --deliver 2>>/tmp/katsuragi-email.log &
fi

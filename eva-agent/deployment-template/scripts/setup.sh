#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# EVA Agent — Interactive Client Setup
# ═══════════════════════════════════════════════════════════════
# Run this once when onboarding a new client.
# It collects company info, integration credentials, and users,
# then writes .env and updates config/agent-config.yaml.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$ROOT_DIR/config/agent-config.yaml"
ENV_FILE="$ROOT_DIR/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

banner() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     EVA Agent — Client Setup Wizard       ║${NC}"
    echo -e "${BLUE}║     Evangelion Project                     ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
    echo ""
}

prompt() {
    local var_name="$1"
    local prompt_text="$2"
    local default="${3:-}"
    local value

    if [[ -n "$default" ]]; then
        read -rp "$(echo -e "${GREEN}?${NC} ${prompt_text} [${default}]: ")" value
        value="${value:-$default}"
    else
        read -rp "$(echo -e "${GREEN}?${NC} ${prompt_text}: ")" value
    fi
    eval "$var_name=\"$value\""
}

prompt_secret() {
    local var_name="$1"
    local prompt_text="$2"
    local value

    read -srp "$(echo -e "${GREEN}?${NC} ${prompt_text}: ")" value
    echo ""
    eval "$var_name=\"$value\""
}

section() {
    echo ""
    echo -e "${YELLOW}── $1 ──${NC}"
    echo ""
}

# ─── Start ───────────────────────────────────────────────────

banner

echo "This wizard will configure EVA for a new client."
echo "You'll need: company info, Procore API creds, DocuSign keys, and SMTP settings."
echo ""
read -rp "Press Enter to begin..."

# ─── Company Info ────────────────────────────────────────────

section "Company Information"

prompt COMPANY_NAME "Company legal name"
prompt COMPANY_SHORT "Short name / abbreviation" "$(echo "$COMPANY_NAME" | awk '{print $1}')"
prompt COMPANY_TYPE "Company type (general_contractor / developer / subcontractor)" "general_contractor"
prompt COMPANY_REGION "Region" "South Florida"
prompt COMPANY_LICENSE "State contractor license number (CGC/CBC)"
prompt CONTACT_NAME "Primary contact name"
prompt CONTACT_EMAIL "Primary contact email"
prompt CONTACT_PHONE "Primary contact phone"

# ─── Anthropic ───────────────────────────────────────────────

section "AI Model Configuration"

prompt_secret ANTHROPIC_API_KEY "Anthropic API Key (sk-ant-...)"

# ─── Procore ─────────────────────────────────────────────────

section "Procore Integration"

prompt PROCORE_ENABLED "Enable Procore? (yes/no)" "yes"

if [[ "$PROCORE_ENABLED" == "yes" ]]; then
    prompt PROCORE_COMPANY_ID "Procore Company ID"
    prompt_secret PROCORE_CLIENT_ID "Procore Client ID"
    prompt_secret PROCORE_CLIENT_SECRET "Procore Client Secret"
    prompt PROCORE_ENV "Procore environment (production/sandbox)" "production"
else
    PROCORE_COMPANY_ID=""
    PROCORE_CLIENT_ID=""
    PROCORE_CLIENT_SECRET=""
    PROCORE_ENV="production"
fi

# ─── DocuSign ────────────────────────────────────────────────

section "DocuSign Integration"

prompt DOCUSIGN_ENABLED "Enable DocuSign? (yes/no)" "yes"

if [[ "$DOCUSIGN_ENABLED" == "yes" ]]; then
    prompt DOCUSIGN_ACCOUNT_ID "DocuSign Account ID"
    prompt_secret DOCUSIGN_INTEGRATION_KEY "DocuSign Integration Key"
    prompt_secret DOCUSIGN_SECRET_KEY "DocuSign Secret Key"
    prompt DOCUSIGN_ENV "DocuSign environment (production/demo)" "production"
else
    DOCUSIGN_ACCOUNT_ID=""
    DOCUSIGN_INTEGRATION_KEY=""
    DOCUSIGN_SECRET_KEY=""
    DOCUSIGN_ENV="production"
fi

# ─── Email ───────────────────────────────────────────────────

section "Email (SMTP) Configuration"

prompt SMTP_HOST "SMTP host" "smtp.office365.com"
prompt SMTP_PORT "SMTP port" "587"
prompt SMTP_USER "SMTP username (email)"
prompt_secret SMTP_PASSWORD "SMTP password"
prompt SMTP_FROM "From address" "$SMTP_USER"

# ─── Users ───────────────────────────────────────────────────

section "User Setup"

echo "Add users who will interact with EVA."
echo "You can add more later in config/agent-config.yaml."
echo ""

USERS_YAML=""
USER_COUNT=0

while true; do
    USER_COUNT=$((USER_COUNT + 1))
    echo -e "${BLUE}User #${USER_COUNT}${NC}"
    
    prompt USER_NAME "  Full name"
    prompt USER_EMAIL "  Email"
    prompt USER_ROLE "  Role (admin/project_manager/superintendent/executive)" "project_manager"
    
    USERS_YAML="${USERS_YAML}
  - id: \"user-$(printf '%03d' $USER_COUNT)\"
    name: \"${USER_NAME}\"
    email: \"${USER_EMAIL}\"
    role: \"${USER_ROLE}\"
    projects: [\"all\"]
    channels:
      - type: \"email\"
        address: \"${USER_EMAIL}\""

    echo ""
    read -rp "Add another user? (yes/no) [no]: " MORE_USERS
    MORE_USERS="${MORE_USERS:-no}"
    [[ "$MORE_USERS" == "yes" ]] || break
    echo ""
done

# ─── Server Settings ─────────────────────────────────────────

section "Server Configuration"

prompt AGENT_PORT "Agent port" "3000"
POSTGRES_PASSWORD="$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)"
echo -e "  ${GREEN}✓${NC} Generated secure PostgreSQL password"

# ─── Write .env ──────────────────────────────────────────────

section "Writing Configuration"

cat > "$ENV_FILE" << EOF
# EVA Agent — Environment Variables
# Generated by setup.sh on $(date -Iseconds)
# Client: ${COMPANY_NAME}

# ─── Server ─────────────────────────────────────
AGENT_PORT=${AGENT_PORT}

# ─── Database ───────────────────────────────────
POSTGRES_USER=eva
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=eva_agent

# ─── AI ─────────────────────────────────────────
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# ─── Procore ────────────────────────────────────
PROCORE_CLIENT_ID=${PROCORE_CLIENT_ID}
PROCORE_CLIENT_SECRET=${PROCORE_CLIENT_SECRET}
PROCORE_COMPANY_ID=${PROCORE_COMPANY_ID}

# ─── DocuSign ───────────────────────────────────
DOCUSIGN_INTEGRATION_KEY=${DOCUSIGN_INTEGRATION_KEY}
DOCUSIGN_SECRET_KEY=${DOCUSIGN_SECRET_KEY}
DOCUSIGN_ACCOUNT_ID=${DOCUSIGN_ACCOUNT_ID}

# ─── Email (SMTP) ──────────────────────────────
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=${SMTP_PORT}
SMTP_USER=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASSWORD}
SMTP_FROM=${SMTP_FROM}
EOF

chmod 600 "$ENV_FILE"
echo -e "  ${GREEN}✓${NC} .env written (permissions: 600)"

# ─── Update agent-config.yaml ────────────────────────────────

# Use sed for safe in-place replacements
sed -i "s|name: \"ACME Construction Inc.\"|name: \"${COMPANY_NAME}\"|" "$CONFIG_FILE"
sed -i "s|short_name: \"ACME\"|short_name: \"${COMPANY_SHORT}\"|" "$CONFIG_FILE"
sed -i "s|type: \"general_contractor\"|type: \"${COMPANY_TYPE}\"|" "$CONFIG_FILE"
sed -i "s|region: \"South Florida\"|region: \"${COMPANY_REGION}\"|" "$CONFIG_FILE"
sed -i "s|license_number: \"\"|license_number: \"${COMPANY_LICENSE}\"|" "$CONFIG_FILE"

# Replace primary contact
sed -i "/primary_contact:/,/phone:/ {
    s|name: \"\"|name: \"${CONTACT_NAME}\"|
    s|email: \"\"|email: \"${CONTACT_EMAIL}\"|
    s|phone: \"\"|phone: \"${CONTACT_PHONE}\"|
}" "$CONFIG_FILE"

# Replace Procore settings
sed -i "s|company_id: \"\".*# From Procore|company_id: \"${PROCORE_COMPANY_ID}\"          # From Procore|" "$CONFIG_FILE"

# Replace DocuSign settings
sed -i "s|account_id: \"\"$|account_id: \"${DOCUSIGN_ACCOUNT_ID}\"|" "$CONFIG_FILE"

# Replace users section
python3 -c "
import re
with open('$CONFIG_FILE', 'r') as f:
    content = f.read()
# Replace from 'users:' to the next top-level key
users_block = '''users:${USERS_YAML}'''
content = re.sub(r'users:.*?(?=\n# ─── Projects|\nprojects:)', users_block + '\n\n', content, flags=re.DOTALL)
with open('$CONFIG_FILE', 'w') as f:
    f.write(content)
" 2>/dev/null || echo -e "  ${YELLOW}!${NC} Auto-update of users section skipped — edit config/agent-config.yaml manually"

echo -e "  ${GREEN}✓${NC} agent-config.yaml updated"

# ─── Summary ─────────────────────────────────────────────────

section "Setup Complete"

echo -e "  Company:    ${GREEN}${COMPANY_NAME}${NC} (${COMPANY_SHORT})"
echo -e "  Type:       ${COMPANY_TYPE}"
echo -e "  Region:     ${COMPANY_REGION}"
echo -e "  Users:      ${USER_COUNT}"
echo -e "  Procore:    $([ "$PROCORE_ENABLED" = "yes" ] && echo -e "${GREEN}Enabled${NC}" || echo -e "${RED}Disabled${NC}")"
echo -e "  DocuSign:   $([ "$DOCUSIGN_ENABLED" = "yes" ] && echo -e "${GREEN}Enabled${NC}" || echo -e "${RED}Disabled${NC}")"
echo -e "  Port:       ${AGENT_PORT}"
echo ""
echo -e "Next step: ${BLUE}./scripts/deploy.sh${NC}"
echo ""

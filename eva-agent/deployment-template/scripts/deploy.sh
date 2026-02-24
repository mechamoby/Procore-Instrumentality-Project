#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# EVA Agent — Deployment Script
# ═══════════════════════════════════════════════════════════════
# One-command deployment with health checks.
# Run setup.sh first to generate .env and configure the agent.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ─── Pre-flight checks ──────────────────────────────────────

echo -e "${BLUE}EVA Agent — Deployment${NC}"
echo ""

# Check .env exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}✗ .env not found. Run ./scripts/setup.sh first.${NC}"
    exit 1
fi

# Check Docker
if ! command -v docker &>/dev/null; then
    echo -e "${RED}✗ Docker not found. Install Docker Engine 24+.${NC}"
    exit 1
fi

if ! docker compose version &>/dev/null; then
    echo -e "${RED}✗ Docker Compose v2 not found.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Pre-flight checks passed"

# ─── Load port from .env ─────────────────────────────────────

source "$ENV_FILE"
AGENT_PORT="${AGENT_PORT:-3000}"

# ─── Pull latest images ─────────────────────────────────────

echo -e "${BLUE}Pulling images...${NC}"
cd "$ROOT_DIR"
docker compose pull

# ─── Deploy ──────────────────────────────────────────────────

echo -e "${BLUE}Starting services...${NC}"
docker compose up -d

# ─── Health checks ───────────────────────────────────────────

echo ""
echo -e "${BLUE}Waiting for services to be healthy...${NC}"

MAX_WAIT=120
INTERVAL=5
ELAPSED=0

# Wait for PostgreSQL
echo -n "  PostgreSQL: "
while [[ $ELAPSED -lt $MAX_WAIT ]]; do
    if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-eva}" &>/dev/null; then
        echo -e "${GREEN}healthy${NC}"
        break
    fi
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done
[[ $ELAPSED -ge $MAX_WAIT ]] && echo -e "${RED}timeout${NC}"

# Wait for Redis
ELAPSED=0
echo -n "  Redis:      "
while [[ $ELAPSED -lt $MAX_WAIT ]]; do
    if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        echo -e "${GREEN}healthy${NC}"
        break
    fi
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done
[[ $ELAPSED -ge $MAX_WAIT ]] && echo -e "${RED}timeout${NC}"

# Wait for Agent
ELAPSED=0
echo -n "  EVA Agent:  "
while [[ $ELAPSED -lt $MAX_WAIT ]]; do
    if curl -sf "http://localhost:${AGENT_PORT}/health" &>/dev/null; then
        echo -e "${GREEN}healthy${NC}"
        break
    fi
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done
[[ $ELAPSED -ge $MAX_WAIT ]] && echo -e "${RED}timeout${NC}"

# ─── Summary ─────────────────────────────────────────────────

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  EVA Agent deployed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "  Agent URL:  ${BLUE}http://localhost:${AGENT_PORT}${NC}"
echo -e "  Health:     ${BLUE}http://localhost:${AGENT_PORT}/health${NC}"
echo ""
echo -e "  Logs:       docker compose -f ${COMPOSE_FILE} logs -f"
echo -e "  Stop:       docker compose -f ${COMPOSE_FILE} down"
echo -e "  Restart:    docker compose -f ${COMPOSE_FILE} restart"
echo ""

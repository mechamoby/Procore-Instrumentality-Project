# EVA — Client Onboarding Checklist

Step-by-step guide from initial sales meeting to go-live. Target: **complete in one business day**.

---

## Phase 1: Pre-Sales (Before Contract)

- [ ] **Discovery call** — Understand client's project types, team size, pain points
- [ ] **Demo EVA** using sandbox instance
- [ ] **Confirm tech requirements** — Will they provide a closet/server room with power, ethernet, and cooling?
- [ ] **Identify primary contact** — Who will be the admin user and main point of contact?
- [ ] **Confirm integrations** — Do they have Procore? DocuSign? What email system (O365, Google Workspace)?
- [ ] **Contract signed** — MSA + subscription agreement

---

## Phase 2: Pre-Deployment (1-2 days before install)

### Collect from Client

- [ ] Company legal name and contractor license number (CGC/CBC)
- [ ] Primary contact: name, email, phone
- [ ] **User list** with names, emails, and roles:
  - Admin (usually IT or office manager)
  - Project Managers
  - Superintendents
  - Executives
- [ ] **Active project list** — names and Procore project IDs
- [ ] Network info: static IP for the mini-server, DNS preferences, firewall rules for outbound HTTPS

### Collect Integration Credentials

- [ ] **Procore API credentials**
  - Client must create a Procore App (Developer Portal → Create App → Service Account)
  - Provide: Client ID, Client Secret, Company ID
  - Scopes needed: read/write for daily logs, submittals, RFIs, change orders, directory, documents
- [ ] **DocuSign API credentials**
  - Client creates an integration key in DocuSign Admin
  - Provide: Integration Key, Secret Key, Account ID
  - Must authorize the app for production use (not just demo)
- [ ] **SMTP credentials**
  - Host, port, username, password
  - A dedicated `eva@clientdomain.com` mailbox is recommended
  - If O365: may need an App Password or OAuth setup

### Prepare Hardware

- [ ] Mini-server provisioned with:
  - Ubuntu Server 22.04+ or similar
  - Docker Engine 24+ installed
  - Docker Compose v2 installed
  - 8GB+ RAM, 50GB+ SSD
  - SSH access configured
- [ ] Server shipped or on-site

---

## Phase 3: Deployment Day (30 minutes)

### Setup

```bash
# SSH into the mini-server
ssh admin@<server-ip>

# Clone the deployment template
git clone <eva-template-repo> /opt/eva
cd /opt/eva

# Run interactive setup
./scripts/setup.sh
# → Enter company info
# → Enter Procore credentials
# → Enter DocuSign credentials
# → Enter SMTP settings
# → Add users

# Deploy
./scripts/deploy.sh
```

### Verify

- [ ] Health check passes: `curl http://localhost:3000/health`
- [ ] PostgreSQL is running: `docker compose exec postgres pg_isready`
- [ ] Redis is running: `docker compose exec redis redis-cli ping`
- [ ] Agent responds to a test message
- [ ] Procore connection verified — can pull project list
- [ ] DocuSign connection verified — can check account status
- [ ] Email verified — send a test email

### Post-Deploy Configuration

- [ ] Add any additional users to `config/agent-config.yaml`
- [ ] Configure active projects in agent config
- [ ] Set notification preferences (daily report reminders, submittal alerts)
- [ ] Restart agent: `docker compose restart openclaw`

---

## Phase 4: Training & Handoff (same day or next day)

### Admin Training (30 min)
- [ ] Show how to access EVA (web interface / email / Telegram)
- [ ] Explain user roles and how to add/remove users
- [ ] Show config files and how to restart the agent
- [ ] Walk through backup verification: `docker compose exec backup ls /backups/`

### User Training — Project Managers (30 min)
- [ ] Daily workflow: checking submittals, RFIs, change order status
- [ ] Creating and tracking submittals through EVA
- [ ] Generating reports for owner meetings
- [ ] Sending DocuSign envelopes through EVA

### User Training — Superintendents (30 min)
- [ ] Creating daily logs via EVA (conversational flow)
- [ ] Reporting inspections and results
- [ ] Flagging safety issues
- [ ] Checking delivery schedules and submittal status

### User Training — Executives (15 min)
- [ ] Requesting project status summaries
- [ ] Financial reporting: cost-to-complete, change order log, pay app status
- [ ] Portfolio-level dashboards

---

## Phase 5: Go-Live Support (first 2 weeks)

- [ ] **Day 1-3**: Daily check-in with primary contact — any issues?
- [ ] **Day 3**: Review agent logs for errors or permission issues
- [ ] **Week 1**: Verify daily logs are being submitted consistently
- [ ] **Week 1**: Verify submittal tracking is active and reminders are firing
- [ ] **Week 2**: Collect feedback from all user types
- [ ] **Week 2**: Adjust prompts or config based on feedback
- [ ] **End of Week 2**: Formal handoff — client is self-sufficient

---

## Ongoing Maintenance

| Task | Frequency | How |
|------|-----------|-----|
| Check agent health | Daily (automated) | Health endpoint monitoring |
| Review backup files | Weekly | `ls -la` in backup volume |
| Update agent image | Monthly or as released | `docker compose pull && docker compose up -d` |
| Review and rotate API keys | Quarterly | Update `.env`, restart |
| Disk space check | Monthly | `df -h` on server |

---

## Troubleshooting Quick Reference

| Symptom | Check |
|---------|-------|
| Agent not responding | `docker compose ps` — is the container running? |
| Procore data stale | Check sync interval in config, verify API creds |
| Email not sending | Verify SMTP creds, check firewall for port 587 outbound |
| DocuSign errors | Check if integration key is authorized for production |
| Slow responses | Check RAM usage: `docker stats`, consider upgrading to 16GB |
| Database errors | `docker compose logs postgres`, check disk space |

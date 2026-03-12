# Docker Compose Health Snapshot

## Date: 2026-03-12T02:04:00Z
## Docker Compose File: /home/moby/.openclaw/workspace/nerv-deploy-repo/docker-compose.yml
## Deploy Repo Branch: ops/phase3 @ cc58a23
## Compose Projects Active: nerv-deploy (15 services running), nerv-deploy-repo (2 services restarting)

## Summary

- Total services defined in docker-compose.yml: **19**
- HEALTHY: **11**
- RUNNING_UNVERIFIED: **4**
- DEGRADED: **0**
- EXITED: **0**
- FAILED: **2** (intelligence-engine, command-center-api)
- MISSING: **2** (openclaw, caddy)

## Critical Finding

Two Docker Compose projects are running from the same `docker-compose.yml`:
- `nerv-deploy` — 15 services, launched correctly with shared `nerv-network`
- `nerv-deploy-repo` — 2 services (intelligence-engine, command-center-api), launched separately and isolated in a different network

The 2 FAILED services cannot resolve the hostname `postgres` because they are on a separate Docker network from the `nerv-deploy` project's postgres container. This is a **deployment configuration issue**, not a code issue.

---

## Service Detail

### 1. openclaw
- **Status:** MISSING
- **Image:** ghcr.io/evangelion-project/openclaw:latest
- **Ports:** ${OPENCLAW_PORT:-3000}:3000
- **Health Check:** Defined (curl http://localhost:3000/health)
- **Notes:** No container exists. Image may not be available (private registry). Port 3000 returns connection refused.

---

### 2. nerv-interface
- **Status:** HEALTHY
- **Image:** nerv-deploy-nerv-interface (local build)
- **Container:** nerv-interface
- **Ports:** 0.0.0.0:8080->8080/tcp
- **Health Check:** Defined, passing
- **Connectivity Test:** `curl http://localhost:8080/health` → HTTP 200
- **Uptime:** Up 2 hours

---

### 3. postgres
- **Status:** HEALTHY
- **Image:** pgvector/pgvector:pg16
- **Container:** nerv-postgres
- **Ports:** 5432/tcp (internal only, external access commented out)
- **Health Check:** Defined (pg_isready), passing
- **Connectivity Test:** `docker exec nerv-postgres pg_isready -U eva -d nerv` → accepting connections
- **Uptime:** Up 2 hours
- **Memory Limit:** 2g

---

### 4. redis
- **Status:** HEALTHY
- **Image:** redis:7-alpine
- **Container:** nerv-redis
- **Ports:** 6379/tcp (internal only)
- **Health Check:** Defined (redis-cli ping), passing
- **Connectivity Test:** `redis-cli ping` → PONG
- **Uptime:** Up 2 hours
- **Memory Limit:** 512m
- **Config:** appendonly=yes, maxmemory=512mb, LRU eviction

---

### 5. watchdog
- **Status:** RUNNING_UNVERIFIED
- **Image:** nerv-deploy-watchdog (local build)
- **Container:** nerv-watchdog
- **Ports:** None exposed
- **Health Check:** Not defined
- **Uptime:** Up 2 hours
- **Logs (last observation):** Health check: 6/6 services healthy (monitors: eva-sentry, token-guardian, webhook-receiver, smartsheet-adapter, portal-auth, nerv-interface)
- **Notes:** Monitoring 6 of 19 services. Does not monitor intelligence-engine or command-center-api despite listing them as dependencies in docker-compose.yml.
- **Memory Limit:** 512m

---

### 6. portal-auth
- **Status:** HEALTHY
- **Image:** nerv-deploy-portal-auth (local build)
- **Container:** nerv-portal-auth
- **Ports:** 127.0.0.1:8094->8094/tcp
- **Health Check:** Defined (curl http://localhost:8094/health), passing
- **Connectivity Test:** `curl http://127.0.0.1:8094/health` → HTTP 200
- **Uptime:** Up 2 hours
- **Memory Limit:** 512m

---

### 7. smartsheet-adapter
- **Status:** HEALTHY
- **Image:** nerv-deploy-smartsheet-adapter (local build)
- **Container:** nerv-smartsheet-adapter
- **Ports:** 127.0.0.1:8093->8093/tcp
- **Health Check:** Defined (curl http://localhost:8093/health), passing
- **Connectivity Test:** `curl http://127.0.0.1:8093/health` → HTTP 200
- **Uptime:** Up 2 hours
- **Memory Limit:** 512m

---

### 8. eva-sentry
- **Status:** HEALTHY
- **Image:** nerv-deploy-eva-sentry (local build)
- **Container:** nerv-eva-sentry
- **Ports:** 127.0.0.1:8092->8092/tcp
- **Health Check:** Defined (curl http://localhost:8092/health), passing
- **Connectivity Test:** `curl http://127.0.0.1:8092/health` → HTTP 200
- **Uptime:** Up 2 hours
- **Memory Limit:** 1g

---

### 9. token-guardian
- **Status:** HEALTHY
- **Image:** nerv-deploy-token-guardian (local build)
- **Container:** nerv-token-guardian
- **Ports:** 127.0.0.1:8091->8091/tcp
- **Health Check:** Defined (curl http://localhost:8091/health), passing
- **Connectivity Test:** `curl http://127.0.0.1:8091/health` → HTTP 200
- **Uptime:** Up 2 hours
- **Memory Limit:** 512m

---

### 10. webhook-receiver
- **Status:** HEALTHY
- **Image:** nerv-deploy-webhook-receiver (local build)
- **Container:** nerv-webhook-receiver
- **Ports:** 127.0.0.1:8090->8090/tcp
- **Health Check:** Defined (curl http://localhost:8090/health), passing
- **Connectivity Test:** `curl http://127.0.0.1:8090/health` → HTTP 200
- **Uptime:** Up 2 hours
- **Memory Limit:** 512m

---

### 11. inbox-watcher
- **Status:** RUNNING_UNVERIFIED
- **Image:** nerv-deploy-inbox-watcher (local build)
- **Container:** nerv-inbox-watcher
- **Ports:** None exposed
- **Health Check:** Not defined
- **Uptime:** Up 2 hours
- **Logs (last observation):** `Discovered 0 _Inbox folders` (polling every 60s, no errors)
- **Notes:** Running normally but no inboxes configured. No health check endpoint.
- **Memory Limit:** 512m

---

### 12. embedding-pipeline
- **Status:** HEALTHY
- **Image:** nerv-deploy-embedding-pipeline (local build)
- **Container:** nerv-embedding-pipeline
- **Ports:** None exposed externally
- **Health Check:** Defined, passing (Docker reports "healthy")
- **Uptime:** Up 2 hours
- **Memory Limit:** 4g
- **Notes:** Highest memory allocation of any service. No external port — health check runs internally.

---

### 13. notification-engine
- **Status:** HEALTHY
- **Image:** nerv-deploy-notification-engine (local build)
- **Container:** nerv-notification-engine
- **Ports:** 127.0.0.1:8096->8096/tcp
- **Health Check:** Defined (curl http://localhost:8096/health), passing
- **Connectivity Test:** `curl http://127.0.0.1:8096/health` → HTTP 200
- **Uptime:** Up 2 hours
- **Memory Limit:** 512m

---

### 14. command-center-api
- **Status:** FAILED (Restarting)
- **Image:** nerv-deploy-repo-command-center-api (local build)
- **Container:** steelsync-command-center-api
- **Ports:** 127.0.0.1:8097->8097 (not reachable)
- **Health Check:** Defined (curl http://localhost:8097/health) — not passing
- **Connectivity Test:** `curl http://127.0.0.1:8097/health` → HTTP 000 (connection refused)
- **Error:** `socket.gaierror: [Errno -5] No address associated with hostname` — cannot resolve `postgres` hostname
- **Root Cause:** Container was launched in compose project `nerv-deploy-repo` which has its own isolated Docker network. The `postgres` service is in compose project `nerv-deploy` on network `nerv-deploy_nerv-network`. This container is on `nerv-deploy-repo_nerv-network` — a completely separate network.
- **Error Log (tail):**
```
File "/usr/local/lib/python3.12/socket.py", line 978, in getaddrinfo
    for res in _socket.getaddrinfo(host, port, family, type, proto, flags):
socket.gaierror: [Errno -5] No address associated with hostname
ERROR:    Application startup failed. Exiting.
```

---

### 15. intelligence-engine
- **Status:** FAILED (Restarting)
- **Image:** nerv-deploy-repo-intelligence-engine (local build)
- **Container:** steelsync-intelligence-engine
- **Ports:** 127.0.0.1:8098->8098 (not reachable)
- **Health Check:** Defined (curl http://localhost:8098/health) — not passing
- **Connectivity Test:** `curl http://127.0.0.1:8098/health` → HTTP 000 (connection refused)
- **Error:** `psycopg2.OperationalError: could not translate host name "postgres" to address: No address associated with hostname`
- **Root Cause:** Same as command-center-api — launched in a separate compose project with an isolated network that cannot reach the `postgres` container.
- **Error Log (tail):**
```
File "/app/steelsync_db.py", line 64, in get_pool
    _pool = psycopg2.pool.ThreadedConnectionPool(
psycopg2.OperationalError: could not translate host name "postgres" to address: No address associated with hostname
ERROR:    Application startup failed. Exiting.
```

---

### 16. caddy
- **Status:** MISSING
- **Image:** caddy:2-alpine
- **Ports:** 80:80, 443:443
- **Health Check:** Not defined in docker-compose.yml
- **Notes:** No container exists. Caddy was defined in the compose file but never started. Port 80 and 443 return connection refused. Likely not started because it depends on nerv-interface and intelligence-engine, and intelligence-engine is failing.

---

### 17. drawing-intel
- **Status:** HEALTHY
- **Image:** nerv-deploy-drawing-intel (local build)
- **Container:** nerv-drawing-intel
- **Ports:** 127.0.0.1:8095->8095/tcp
- **Health Check:** Defined (curl http://localhost:8095/health), passing
- **Connectivity Test:** `curl http://127.0.0.1:8095/health` → HTTP 200
- **Uptime:** Up 2 hours
- **Memory Limit:** 1g

---

### 18. backup
- **Status:** RUNNING_UNVERIFIED
- **Image:** postgres:16-alpine
- **Container:** nerv-backup
- **Ports:** 5432/tcp (artifact of base image, not used)
- **Health Check:** Not defined
- **Uptime:** Up 2 hours
- **Logs (last observation):** `[Thu Mar 12 02:00:00 UTC 2026] Backup completed` — daily cron at 02:00 UTC running successfully. Retention: 30 days.
- **Notes:** Running pg_dump cron job. Last 4 backups all successful.

---

### 19. healthcheck
- **Status:** RUNNING_UNVERIFIED
- **Image:** alpine:latest
- **Container:** nerv-healthcheck
- **Ports:** None
- **Health Check:** Not defined (service IS the health checker)
- **Uptime:** Up 2 hours
- **Logs (last observation):** `All services healthy` — checks: nerv-interface, eva-sentry, token-guardian, smartsheet-adapter, portal-auth, webhook-receiver, drawing-intel
- **Notes:** Monitors 7 services. Does not monitor intelligence-engine, command-center-api, notification-engine, embedding-pipeline, inbox-watcher, openclaw, or caddy.

---

## Additional Observations

### Orphaned Containers
Two exited containers exist outside any compose project:
- `optimistic_kepler` — Exited (0) 9 days ago, image `582fb000a50b`
- `sweet_chebyshev` — Exited (0) 9 days ago, image `582fb000a50b`

These appear to be manually-run containers (Docker-assigned names). Not blocking anything.

### Compose Project Split Issue
The root cause of the 2 FAILED services is that `docker compose up` was run twice from the same directory but Docker assigned different project names:
- `nerv-deploy` (15 services) — original launch, all services on `nerv-deploy_nerv-network`
- `nerv-deploy-repo` (2 services) — later launch of just intelligence-engine and command-center-api, isolated on `nerv-deploy-repo_nerv-network`

**Fix (not applied — report only):** Stop the `nerv-deploy-repo` project and relaunch those 2 services under the `nerv-deploy` project:
```bash
cd /home/moby/.openclaw/workspace/nerv-deploy-repo
docker compose -p nerv-deploy-repo down
docker compose -p nerv-deploy up -d intelligence-engine command-center-api
```

### Services Without Health Checks
4 services lack health check definitions: watchdog, inbox-watcher, backup, healthcheck. These are utility/monitoring services, so the absence is understandable but should be documented.

### Monitoring Coverage Gap
Both the watchdog and healthcheck services only monitor a subset of services. Neither monitors the 2 newest services (intelligence-engine, command-center-api), notification-engine, embedding-pipeline, or inbox-watcher.

# Recommended Software for Manjaro KDE AI Agent Workstation

**Machine:** Intel i7-1370P | 62GB RAM | 932GB NVMe | Manjaro KDE  
**Purpose:** Always-on AI agent development & construction business operations  
**Already installed:** Python 3.14, Node.js v25, Go, Git, SQLite, ripgrep, htop, base-devel, yay (AUR)  
**Date:** 2026-02-17

---

## 1. Development Tools

| Software | What it does | Why useful | Install | Priority |
|----------|-------------|-----------|---------|----------|
| **Neovim** | Modern terminal editor | Fast editing from CLI/agents | `pacman -S neovim` | Essential |
| **VS Code** | GUI IDE with extensions | Visual debugging, extension ecosystem | `yay -S visual-studio-code-bin` | Recommended |
| **tmux** | Terminal multiplexer | Persistent sessions for always-on agent work | `pacman -S tmux` | Essential |
| **Rust (rustup)** | Rust toolchain | Build fast CLI tools, many modern tools need it | `pacman -S rustup` then `rustup default stable` | Recommended |
| **JDK (OpenJDK)** | Java runtime/compiler | Some enterprise tools, PDF libs need it | `pacman -S jdk-openjdk` | Recommended |
| **jq** | JSON processor | Parse API responses, config files | `pacman -S jq` | Essential |
| **yq** | YAML/TOML/XML processor | Config file manipulation | `pacman -S yq` | Recommended |
| **fd** | Fast file finder | Better `find` for agents searching files | `pacman -S fd` | Essential |
| **bat** | Cat with syntax highlighting | Better file viewing | `pacman -S bat` | Recommended |
| **fzf** | Fuzzy finder | Interactive search/selection | `pacman -S fzf` | Recommended |
| **direnv** | Per-directory env vars | Manage project-specific environments | `pacman -S direnv` | Recommended |
| **shellcheck** | Shell script linter | Validate automation scripts | `pacman -S shellcheck` | Recommended |
| **strace / ltrace** | System call tracers | Debug agent processes | `pacman -S strace ltrace` | Nice-to-have |

---

## 2. Document Handling

| Software | What it does | Why useful | Install | Priority |
|----------|-------------|-----------|---------|----------|
| **LibreOffice** | Full office suite | Open/edit/convert Word, Excel, PowerPoint — construction contracts, bids, invoices | `pacman -S libreoffice-fresh` | Essential |
| **Pandoc** | Universal document converter | Convert between MD, DOCX, PDF, HTML — automate report generation | `pacman -S pandoc` | Essential |
| **Tesseract OCR** | Optical character recognition | Extract text from scanned construction plans, permits, receipts | `pacman -S tesseract tesseract-data-eng` | Essential |
| **Poppler (pdftotext etc)** | PDF utilities | Extract text from PDFs, split/merge — process construction docs | `pacman -S poppler` | Essential |
| **qpdf** | PDF manipulation | Merge, split, encrypt PDFs programmatically | `pacman -S qpdf` | Recommended |
| **Ghostscript** | PostScript/PDF processor | PDF rendering, conversion, compression | `pacman -S ghostscript` | Recommended |
| **img2pdf** | Images to PDF | Convert construction photos to PDF reports | `pip install img2pdf` | Recommended |
| **WeasyPrint** | HTML to PDF | Generate styled PDF reports/invoices from templates | `pip install weasyprint` | Recommended |
| **OCRmyPDF** | Add OCR layer to PDFs | Make scanned construction docs searchable | `pip install ocrmypdf` | Essential |

---

## 3. Data & Visualization

| Software | What it does | Why useful | Install | Priority |
|----------|-------------|-----------|---------|----------|
| **PostgreSQL** | Relational database | Store construction project data, client records, agent state | `pacman -S postgresql` | Essential |
| **Redis** | In-memory data store | Caching, queues, pub/sub for agent coordination | `pacman -S redis` | Essential |
| **DuckDB** | Analytical SQL engine | Fast analytics on CSV/Parquet — analyze project data | `pacman -S duckdb` or `pip install duckdb` | Recommended |
| **Python: pandas** | Data manipulation | Process construction estimates, schedules, financial data | `pip install pandas` | Essential |
| **Python: matplotlib** | Plotting library | Generate charts for reports/dashboards | `pip install matplotlib` | Recommended |
| **Python: plotly** | Interactive charts | Web-ready dashboards for construction project status | `pip install plotly` | Recommended |
| **Python: openpyxl** | Excel read/write | Programmatically create/edit construction spreadsheets | `pip install openpyxl` | Essential |
| **csvkit** | CSV utilities | Quick CLI data wrangling | `pip install csvkit` | Recommended |

---

## 4. Communication & Business

| Software | What it does | Why useful | Install | Priority |
|----------|-------------|-----------|---------|----------|
| **msmtp** | SMTP client | Send emails from CLI/agents — notifications, reports | `pacman -S msmtp msmtp-mta` | Essential |
| **neomutt** | Terminal email client | Read/manage email from terminal | `pacman -S neomutt` | Recommended |
| **khal** | CLI calendar | View/manage calendar events | `pip install khal` | Recommended |
| **vdirsyncer** | CalDAV/CardDAV sync | Sync calendar/contacts locally | `pip install vdirsyncer` | Recommended |
| **w3m** | Text web browser | Quick web content extraction | `pacman -S w3m` | Nice-to-have |

---

## 5. DevOps & Deployment

| Software | What it does | Why useful | Install | Priority |
|----------|-------------|-----------|---------|----------|
| **Docker + Docker Compose** | Containerization | Isolate services, deploy apps, run databases | `pacman -S docker docker-compose` then `sudo systemctl enable --now docker` | Essential |
| **Nginx** | Web server / reverse proxy | Serve web apps, proxy agent services | `pacman -S nginx` | Essential |
| **Caddy** | Auto-HTTPS web server | Zero-config TLS, simpler than nginx for quick deploys | `pacman -S caddy` | Recommended |
| **certbot** | Let's Encrypt SSL | Free SSL certificates | `pacman -S certbot certbot-nginx` | Essential |
| **SSH (OpenSSH)** | Remote access | Already installed; ensure `sshd` enabled for remote management | `sudo systemctl enable --now sshd` | Essential |
| **Wireguard** | VPN | Secure tunnel to construction sites, remote access | `pacman -S wireguard-tools` | Recommended |
| **lazydocker** | Docker TUI | Monitor containers visually | `yay -S lazydocker` | Nice-to-have |
| **ctop** | Container top | Quick container monitoring | `yay -S ctop-bin` | Nice-to-have |
| **Ansible** | Configuration management | Automate server setup, manage multiple machines | `pacman -S ansible` | Recommended |

---

## 6. AI/ML Tools

| Software | What it does | Why useful | Install | Priority |
|----------|-------------|-----------|---------|----------|
| **Ollama** | Local LLM runner | Run local models for testing, fallback, cheap inference | `yay -S ollama` | Essential |
| **Python: langchain** | LLM framework | Build agent chains for construction workflows | `pip install langchain` | Recommended |
| **Python: scikit-learn** | Classical ML | Classification, regression on construction data | `pip install scikit-learn` | Recommended |
| **Python: sentence-transformers** | Embeddings | Semantic search over construction docs | `pip install sentence-transformers` | Recommended |
| **Python: chromadb** | Vector database | Store/query document embeddings | `pip install chromadb` | Recommended |
| **Python: PyPDF2 / pdfplumber** | PDF parsing | Extract structured data from construction PDFs | `pip install pdfplumber` | Essential |
| **Python: Pillow** | Image processing | Process construction site photos, plans | `pip install Pillow` | Essential |
| **Python: httpx** | Async HTTP client | Fast API calls to LLMs and services | `pip install httpx` | Essential |
| **Python: pydantic** | Data validation | Structure construction data models | `pip install pydantic` | Essential |

---

## 7. Productivity & Automation

| Software | What it does | Why useful | Install | Priority |
|----------|-------------|-----------|---------|----------|
| **cronie** | Cron daemon | Schedule recurring agent tasks | `pacman -S cronie` then `sudo systemctl enable --now cronie` | Essential |
| **rclone** | Cloud storage sync | Sync files to Google Drive, S3, etc. — share with construction clients | `pacman -S rclone` | Essential |
| **rsync** | File sync/backup | Fast incremental file transfers | `pacman -S rsync` (likely installed) | Essential |
| **trash-cli** | Safe delete | Recoverable deletes (safer than `rm`) | `pacman -S trash-cli` | Essential |
| **CopyQ** | Clipboard manager | KDE clipboard history for development | `pacman -S copyq` | Recommended |
| **xdotool** | X11 automation | Automate GUI interactions if needed | `pacman -S xdotool` | Nice-to-have |
| **entr** | File watcher | Re-run commands when files change | `pacman -S entr` | Recommended |
| **atool** | Archive manager CLI | Handle zip/tar/7z from CLI | `pacman -S atool` | Recommended |

---

## 8. Security

| Software | What it does | Why useful | Install | Priority |
|----------|-------------|-----------|---------|----------|
| **UFW** | Simple firewall | Easy iptables management — protect always-on machine | `pacman -S ufw` then `sudo ufw enable` | Essential |
| **fail2ban** | Brute-force protection | Block SSH/web brute force attempts | `pacman -S fail2ban` | Essential |
| **Timeshift** | System snapshots | Rollback if updates break things | `pacman -S timeshift` | Essential |
| **BorgBackup** | Deduplicating backup | Efficient encrypted backups of business data | `pacman -S borg` | Essential |
| **age** | Modern encryption | Encrypt files simply (replacement for GPG for files) | `pacman -S age` | Recommended |
| **GnuPG** | Encryption/signing | Sign commits, encrypt sensitive construction data | `pacman -S gnupg` (likely installed) | Essential |
| **ClamAV** | Antivirus | Scan uploaded files from clients | `pacman -S clamav` | Recommended |
| **lynis** | Security auditing | Audit system hardening | `pacman -S lynis` | Nice-to-have |

---

## Quick Install Script

```bash
# === System packages (pacman) ===
sudo pacman -S --needed \
  neovim tmux jq yq fd bat fzf direnv shellcheck \
  libreoffice-fresh pandoc tesseract tesseract-data-eng poppler qpdf ghostscript \
  postgresql redis docker docker-compose nginx caddy certbot certbot-nginx \
  wireguard-tools ansible \
  cronie rclone rsync trash-cli copyq entr atool \
  ufw fail2ban timeshift borg age clamav \
  rustup jdk-openjdk strace ltrace w3m neomutt msmtp msmtp-mta

# === AUR packages ===
yay -S --needed visual-studio-code-bin ollama lazydocker ctop-bin

# === Rust toolchain ===
rustup default stable

# === Python packages ===
pip install --user \
  pandas matplotlib plotly openpyxl csvkit \
  pdfplumber Pillow httpx pydantic \
  ocrmypdf img2pdf weasyprint \
  langchain scikit-learn sentence-transformers chromadb \
  khal vdirsyncer duckdb

# === Enable services ===
sudo systemctl enable --now docker cronie sshd postgresql redis
sudo ufw enable
sudo ufw allow ssh
```

---

## Post-Install Notes

1. **Docker:** Add your user to docker group: `sudo usermod -aG docker $USER`
2. **PostgreSQL:** Initialize: `sudo -u postgres initdb -D /var/lib/postgres/data` then create databases
3. **Redis:** Default config is fine for development
4. **UFW:** Configure allowed ports based on your services (80, 443, SSH, Wireguard)
5. **Timeshift:** Set up BTRFS or rsync snapshots on a schedule
6. **BorgBackup:** Set up a remote repo for offsite backups
7. **Ollama:** Pull models: `ollama pull llama3` or similar
8. **Python packages:** Consider using `uv` or virtual environments for isolation

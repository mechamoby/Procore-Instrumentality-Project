# Moby Terminal — Web Interface

Access Moby-1's terminal from Nick's Windows 11 PC via browser.

## Quick Start

From Moby-1:
```bash
# Start the terminal server (password protected)
ttyd -p 7681 -c moby:eva2026 -t fontSize=14 -t theme='{"background":"#1a1b26","foreground":"#c0caf5"}' bash
```

From Nick's PC browser:
```
http://192.168.8.124:7681
```
Login: `moby` / `eva2026`

## Systemd Service (Auto-start)

The service file at `~/.config/systemd/user/moby-terminal.service` runs ttyd on boot.

```bash
# Enable
systemctl --user enable moby-terminal
systemctl --user start moby-terminal

# Check status
systemctl --user status moby-terminal

# View logs
journalctl --user -u moby-terminal -f
```

## Features
- Dark Tokyo Night theme
- Password protected
- Accessible from any device on LAN
- Real-time terminal output
- Full interactive shell

## Security Notes
- Only accessible on LAN (192.168.8.x)
- UFW firewall should allow port 7681 from LAN only
- Basic auth credentials above
- Do NOT expose to internet without TLS

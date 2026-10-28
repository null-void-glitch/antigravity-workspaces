# 🌙 SSH Portfolio TUI

An interactive, terminal-based portfolio that runs over SSH. No web server needed, just pure CLI vibes.

## Features

- **SSH-Accessible**: Access your portfolio directly via SSH—no browser required
- **Beautiful TUI**: Built with Bubble Tea and Lipgloss for a gorgeous terminal experience
- **Lightweight**: Written in Go, runs fast and uses minimal resources
- **Customizable**: Edit `portfolio.yml` to make it yours
- **Zero Dependencies**: Just a single binary, zero runtime deps

## Quick Start

### Prerequisites
- Go 1.21 or higher
- SSH (any client, any platform)

### Build

```bash
./setup.sh
```

Or manually:
```bash
go mod download
go mod tidy
go build -o portfolio-tui
```

### Run

```bash
./portfolio-tui
```

The server starts on `0.0.0.0:2222`

### Connect

From another terminal:
```bash
ssh -p 2222 user@localhost
```

**Any username and password works** (for demo purposes).

## Customization

Edit `portfolio.yml` to add your projects, reflections, and contact info. The TUI will automatically load and display your content.

### YAML Structure

```yaml
name: "Your Name"
bio: "Your bio"

creations:
  - title: "Project Title"
    description: "Short description"
    content: "Detailed content"

reflections:
  - title: "Essay Title"
    content: "Long-form thoughts"

contacts:
  - platform: "GitHub"
    url: "https://..."
```

## Deployment

### Local Network
```bash
# Replace 0.0.0.0 with your machine's IP
./portfolio-tui
# Connect: ssh -p 2222 your-machine-ip
```

### Remote Server
1. Build on your machine or server
2. Copy to server: `scp portfolio-tui user@server:/opt/`
3. Run as daemon using systemd or tmux
4. Point your domain's SSH record to your server

### Systemd Service (Optional)

Create `/etc/systemd/system/portfolio-tui.service`:

```ini
[Unit]
Description=SSH Portfolio TUI
After=network.target

[Service]
Type=simple
User=portfolio
WorkingDirectory=/opt/portfolio-tui
ExecStart=/opt/portfolio-tui/portfolio-tui
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable portfolio-tui
sudo systemctl start portfolio-tui
```

## Architecture

- **main.go**: SSH server setup and session handler
- **tui.go**: Bubble Tea model and UI logic
- **portfolio.yml**: Your content configuration
- **Binary**: Single self-contained executable

## Security Notes

⚠️ **Current Auth**: Demo mode accepts any username/password. For production:

1. Update `handleSSH()` to verify credentials
2. Use key-based auth (gliderlabs/ssh supports this)
3. Run behind a firewall or on internal network only
4. Generate proper host keys

## Building from Source

```bash
git clone <your-repo>
cd portfolio-tui
go build -o portfolio-tui
./portfolio-tui
```

## Troubleshooting

**"Connection refused"**
- Make sure the server is running: `./portfolio-tui`
- Check if port 2222 is already in use: `lsof -i :2222`

**"Key exchange errors"**
- SSH keys are auto-generated on first run in `.ssh/`
- If corrupt, delete and restart

**"Display issues"**
- Ensure terminal supports 24-bit colors (most modern ones do)
- Try setting: `export TERM=xterm-256color`

## Tech Stack

- **Go 1.21** - Language
- **Bubble Tea** - TUI framework
- **Lipgloss** - Terminal styling
- **gliderlabs/ssh** - SSH server
- **YAML** - Configuration

## License

MIT

---

**Built with 🖤 for the terminal aesthetic**

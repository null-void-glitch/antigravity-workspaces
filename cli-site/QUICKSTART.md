# ⚡ Quick Start (30 seconds)

## TL;DR

```bash
# 1. Build
./setup.sh

# 2. Run
./portfolio-tui

# 3. Connect (in another terminal)
ssh -p 2222 user@localhost

# 4. Login with any username/password
```

Done! You're in your SSH portfolio.

## Keyboard Controls

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate menu |
| `Enter` | Select option |
| `q` | Quit / Go back |
| `?` | Help |

## First Time Setup

1. **Edit your portfolio:**
   ```bash
   vim portfolio.yml
   ```
   - Change `name` and `bio`
   - Add your projects
   - Add your contact info

2. **Rebuild:**
   ```bash
   go build -o portfolio-tui
   ```

3. **Test:**
   ```bash
   ./portfolio-tui &
   ssh -p 2222 localhost
   ```

## Custom Port

Edit `main.go` line 15:
```go
const (
    host = "0.0.0.0"
    port = YOUR_PORT_HERE  // Change this
)
```

Then rebuild.

## Connect from Another Machine

```bash
ssh -p 2222 your-machine-ip
```

Replace `your-machine-ip` with your server's IP or hostname.

## Common Commands

```bash
# Build
go build -o portfolio-tui

# Build + Run
./setup.sh && ./portfolio-tui

# Kill server
pkill portfolio-tui

# Check if running
lsof -i :2222

# View logs
ssh -p 2222 localhost 2>&1
```

## Deploy to VPS

```bash
# On your machine
go build -o portfolio-tui
scp portfolio-tui user@vps.example.com:/home/user/
scp portfolio.yml user@vps.example.com:/home/user/

# On the VPS
cd /home/user
chmod +x portfolio-tui
./portfolio-tui
```

## SSH Key Auth

By default, any password works. To require a specific key:

```bash
# Generate key pair
ssh-keygen -t ed25519 -f id_portfolio

# Update main.go to read from id_portfolio.pub
# Then rebuild
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails | `go mod tidy && go clean -modcache` |
| Port in use | `lsof -i :2222` and `kill` process |
| Can't connect | Make sure `./portfolio-tui` is running |
| SSH error | Try: `ssh -vvv -p 2222 localhost` |

## Next Steps

- Read [README.md](README.md) for full docs
- Read [DEVELOPMENT.md](DEVELOPMENT.md) to extend it
- Deploy on a VPS
- Show it off! 🚀

---

**That's it. Simple, fast, pure CLI. ✨**

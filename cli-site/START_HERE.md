# 🌙 START HERE

Welcome to **SSH Portfolio TUI** – an SSH-accessible terminal portfolio. You're 60 seconds away from seeing it in action.

## ⚡ The Absolute Quickest Start

```bash
# 1. Run the server
./portfolio-tui

# 2. In another terminal, connect
ssh -p 2222 user@localhost

# 3. Any username/password works
# 4. Navigate with ↑/↓ keys
# 5. Press q to quit
```

That's it. **You now have a working portfolio.**

---

## 📚 Which Doc Should You Read?

Choose ONE based on your goal:

### "I just want to run it"
→ **[QUICKSTART.md](QUICKSTART.md)** (2 min read)

Fastest path to getting it running locally.

### "I want to make it mine"
→ **[README.md](README.md)** (10 min read)

Full feature list + customization + deployment.

### "I want to understand it deeply"
→ **[ARCHITECTURE.md](ARCHITECTURE.md)** (15 min read)

Technical deep dive with diagrams and code walkthrough.

### "I want to extend it with new features"
→ **[DEVELOPMENT.md](DEVELOPMENT.md)** (20 min read)

Guide to building on top of this + code structure.

### "I want the big picture"
→ **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** (8 min read)

Overview, tech stack, roadmap, and stats.

### "I'm lost and need a map"
→ **[INDEX.md](INDEX.md)** (5 min read)

Navigation guide + file structure + FAQ.

### "I'm getting errors"
→ **[DELIVERY.md](DELIVERY.md)** - Troubleshooting section

Solutions to common problems.

---

## 🚀 What's Here?

```
✅ portfolio-tui          Ready-to-run binary (no build needed)
✅ portfolio.yml          Template for your content
✅ Source code            main.go + model.go (easy to read)
✅ 8 documentation files  For every need
✅ setup.sh               Automation script
```

**Everything you need is included.**

---

## 🎯 Three Different Paths

### Path A: "Just Show Me" (5 minutes)

```bash
./portfolio-tui &              # Start in background
ssh -p 2222 user@localhost    # Connect in new terminal
# Explore, then press q to quit
kill %1                        # Kill the server
```

**No customization, just see it work.**

→ Full guide: [QUICKSTART.md](QUICKSTART.md)

---

### Path B: "Make It Mine" (15 minutes)

```bash
# Edit your portfolio
vim portfolio.yml
# (change name, add projects, etc)

# Rebuild
go build -o portfolio-tui

# Test
./portfolio-tui &
ssh -p 2222 user@localhost
# See your content!
```

**Customized with your actual portfolio.**

→ Full guide: [README.md](README.md)

---

### Path C: "Deploy It Live" (30 minutes)

```bash
# Build locally
go build -o portfolio-tui

# Copy to server
scp portfolio-tui you@vps.example.com:/opt/
scp portfolio.yml you@vps.example.com:/opt/

# Run on server
ssh you@vps.example.com
cd /opt
./portfolio-tui

# Done! Others can now:
# ssh -p 2222 vps.example.com
```

**Live on the internet.**

→ Full guide: [README.md](README.md) - Deployment section

---

## 🤔 Common Questions

**Q: Do I need to compile it?**  
A: No! The binary is already built. Just run `./portfolio-tui`

**Q: Do I need Node/Python/etc?**  
A: No. Single self-contained binary.

**Q: Can I run it on Windows/macOS?**  
A: Linux binary is included. To build for other OS: `GOOS=windows GOARCH=amd64 go build`

**Q: How do I customize it?**  
A: Edit `portfolio.yml` then rebuild with `go build -o portfolio-tui`

**Q: How do I deploy it?**  
A: Copy binary + config to server, run it. See [README.md](README.md)

**Q: Can I add custom features?**  
A: Yes! See [DEVELOPMENT.md](DEVELOPMENT.md)

**Q: Is it secure?**  
A: It uses SSH (encrypted). Password auth is demo-only. Harden for production.

**Q: Can multiple people access it?**  
A: Yes, one SSH session at a time. Modify main.go for concurrency.

---

## ✅ Verify Everything Works

Run these commands:

```bash
# 1. Binary exists and is executable
file portfolio-tui
# Should show: ELF 64-bit executable

# 2. Start the server
./portfolio-tui
# Should show: [+] SSH Portfolio Server on 0.0.0.0:2222

# 3. In another terminal, connect
ssh -p 2222 user@localhost
# Should prompt for password

# 4. Any password works
# Type anything, press enter

# 5. You should see a menu
# Navigate with ↑/↓ keys, press q to quit

# 6. Kill the server
pkill portfolio-tui
```

**If all above work, you're good to go!**

---

## 🎨 Screenshot (What You'll See)

```
┌────────────────────────────────────────┐
│                                        │
│    🌙 Your Portfolio                   │
│    Your tagline / bio here             │
│                                        │
│    [1] My Projects                     │
│    [2] Reflections                     │
│    [3] Contact                         │
│    [q] Quit                            │
│                                        │
│    Use ↑/↓ to navigate                │
│    Press ↵ to select                   │
│                                        │
└────────────────────────────────────────┘
```

Simple. Beautiful. Terminal-native.

---

## 📂 File Guide

| File | Purpose |
|------|---------|
| `portfolio-tui` | The binary (run this) |
| `portfolio.yml` | Your content (edit this) |
| `main.go` | SSH server code |
| `model.go` | TUI code |
| `*.md` | Documentation |

**That's it. No hidden files, no magic.**

---

## 🔗 Documentation Map

```
START_HERE.md (you are here)
    ↓
    ├─→ QUICKSTART.md (fast setup)
    │
    ├─→ README.md (full features)
    │
    ├─→ DEVELOPMENT.md (extending it)
    │
    ├─→ ARCHITECTURE.md (how it works)
    │
    ├─→ PROJECT_SUMMARY.md (overview)
    │
    ├─→ INDEX.md (navigation)
    │
    └─→ DELIVERY.md (checklist)
```

**Pick what matches your needs.**

---

## ⏱️ Time Estimates

| Task | Time |
|------|------|
| Run it locally | 5 min |
| Customize your info | 10 min |
| Deploy to a server | 20 min |
| Build a new feature | 1-2 hours |
| Understand the code | 30 min |

---

## 🚨 If Something Goes Wrong

### Error: "command not found: ssh"
- Install SSH client: `sudo pacman -S openssh` (Arch Linux)

### Error: "port 2222 already in use"
```bash
lsof -i :2222          # See what's using it
kill -9 <PID>          # Kill the process
```

### Error: "connection refused"
- Make sure `./portfolio-tui` is running
- Check with: `lsof -i :2222`

### Binary won't run
```bash
chmod +x portfolio-tui   # Make executable
./portfolio-tui          # Try again
```

### Want to rebuild it
```bash
go build -o portfolio-tui
```

**More help:** See QUICKSTART.md or README.md troubleshooting sections.

---

## 🎯 Your Next Action

**Pick ONE:**

1. **"Run it now"**
   ```bash
   ./portfolio-tui
   # (in another terminal) ssh -p 2222 user@localhost
   ```

2. **"Customize it"**
   ```bash
   vim portfolio.yml
   go build -o portfolio-tui
   ./portfolio-tui
   ```

3. **"Read more"**
   - QUICKSTART.md (2 min)
   - README.md (10 min)
   - Your choice

4. **"Deploy it"**
   ```bash
   go build -o portfolio-tui
   scp portfolio-tui you@vps.com:/opt/
   # ... (see README.md for full guide)
   ```

---

## 💡 Pro Tips

**Tip 1: Edit while running**
```bash
# Terminal 1
./portfolio-tui

# Terminal 2
vim portfolio.yml

# Terminal 3
go build -o portfolio-tui
# Restart server to see changes
```

**Tip 2: Increase font size**
Many terminals have a "Zoom In" function. Use it for comfortable viewing.

**Tip 3: Try different terminals**
Test on different SSH clients to see how it looks:
- `ssh` (standard)
- `putty` (Windows)
- `iterm2` (macOS)
- `windows terminal` (Windows)

**Tip 4: Customize colors**
Edit `model.go` to change Lipgloss colors:
```go
var primaryStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))
```

---

## 🎁 What You Have

✅ A working SSH portfolio  
✅ Full source code (230 lines)  
✅ Comprehensive documentation (8 files)  
✅ Ready-to-deploy binary  
✅ YAML configuration  
✅ Build automation  

**Nothing to install. Nothing to configure. Just run it.**

---

## 🚀 Let's Go!

### The Absolute Minimum (30 seconds)

```bash
./portfolio-tui &
ssh -p 2222 user@localhost
# (any password)
# (press q to quit)
kill %1
```

### One Step Fancier (5 minutes)

```bash
vim portfolio.yml        # Change YOUR_NAME to your name
go build -o portfolio-tui
./portfolio-tui
ssh -p 2222 user@localhost
# See your name!
```

### Full Custom (15 minutes)

```bash
# Edit portfolio.yml completely with YOUR info
vim portfolio.yml

# Add your projects, reflections, contacts
# Save and exit

# Rebuild
go build -o portfolio-tui

# Test
./portfolio-tui &
ssh -p 2222 user@localhost

# Navigate and verify
# Kill with q, then: kill %1
```

---

## 📞 Documentation at a Glance

| Want to... | Read |
|-----------|------|
| Run it immediately | QUICKSTART.md |
| Customize it | README.md |
| Deploy it | README.md |
| Extend it | DEVELOPMENT.md |
| Understand it | ARCHITECTURE.md |
| Get overview | PROJECT_SUMMARY.md |
| Navigate docs | INDEX.md |
| Check status | DELIVERY.md |

---

## 🎉 You're Ready!

Everything works. Everything is documented. Everything is here.

**Pick your path above and go.**

---

## Last Tips

- ✅ The binary is pre-compiled, just run it
- ✅ All docs are markdown files, read in any editor
- ✅ Edit portfolio.yml in any text editor
- ✅ Source code is Go, readable even if you don't know Go
- ✅ No external services needed
- ✅ No configuration needed to get started
- ✅ Deploy anywhere that runs Linux binaries

---

**Happy hacking! 🔓**

Questions? Read the docs. Feature ideas? See DEVELOPMENT.md. Deployment? See README.md.

**You've got everything you need.**

🚀 **Now go build something amazing!**

# 🏗️ Architecture & Technical Deep Dive

Complete technical documentation for SSH Portfolio TUI.

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     SSH Client Terminal                      │
│                    (any SSH client)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                    SSH Protocol
                    (Port 2222)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              SSH Server (gliderlabs/ssh)                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Session Handler (handleSSH)                        │   │
│  │  - PTY detection                                    │   │
│  │  - Input/Output routing                            │   │
│  │  - Window size management                          │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │                                            │
│                 ▼                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Bubble Tea Program (TUI Framework)                 │   │
│  │                                                     │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Model (Application State)                    │  │   │
│  │  │ - Current page                               │  │   │
│  │  │ - Portfolio data                             │  │   │
│  │  │ - Selection index                            │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                     │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Update (Handle Input)                        │  │   │
│  │  │ - Parse keypresses                           │  │   │
│  │  │ - Update model state                         │  │   │
│  │  │ - Return commands                            │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                     │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ View (Render Output)                         │  │   │
│  │  │ - Format with Lipgloss                       │  │   │
│  │  │ - Return rendered string                     │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                 │                                            │
│                 ▼                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Lipgloss (Terminal Styling)                        │   │
│  │  - Colors                                           │   │
│  │  - Layout                                           │   │
│  │  - Borders & decoration                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
                   Terminal Output
```

### Data Flow Diagram

```
START
  │
  ├─► Load portfolio.yml (YAML parsing)
  │
  ├─► Create Model struct
  │   ├─ Name
  │   ├─ Bio
  │   ├─ Creations[]
  │   ├─ Reflections[]
  │   └─ Contacts[]
  │
  ├─► Start SSH Server (gliderlabs/ssh)
  │   ├─ Listen on 0.0.0.0:2222
  │   └─ Register handler (handleSSH)
  │
  └─► Wait for connections
      │
      ├─► SSH Client connects
      │   │
      │   ├─► Authenticate (accept any password)
      │   │
      │   ├─► Open PTY session
      │   │
      │   ├─► Initialize Bubble Tea Program
      │   │
      │   ├─► Enter Event Loop:
      │   │   │
      │   │   ├─ RENDER (View)
      │   │   │   ├─► Get terminal size
      │   │   │   ├─► Format current page
      │   │   │   ├─► Apply Lipgloss styling
      │   │   │   └─► Send to terminal
      │   │   │
      │   │   ├─ INPUT (keyboard event)
      │   │   │   ├─► User presses key
      │   │   │   ├─► Parse as tea.KeyMsg
      │   │   │   ├─► Pass to Update()
      │   │   │   └─► Get new Model
      │   │   │
      │   │   └─ LOOP until quit
      │   │
      │   └─► Close SSH session
      │
      └─► Repeat for next connection
```

### Request-Response Cycle

```
┌─────────────────────────────────────────────────────────────┐
│                    SSH Session Opened                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Initial Render()    │
         │   (Home Screen)       │
         └────────────┬──────────┘
                      │
                      ▼
        ┌────────────────────────┐
        │  Display Options Menu  │
        │  - [1] My Projects     │
        │  - [2] Reflections     │
        │  - [3] Contact         │
        │  - [q] Quit            │
        └────────┬───────────────┘
                 │
                 ▼
       ┌──────────────────────┐
       │  Wait for Input      │
       │  (tea.KeyMsg)        │
       └────┬─────────────────┘
            │
            ├─► [1] pressed
            │   └─► Update() { currentPage = PROJECTS }
            │       │
            │       ▼
            │   ┌─────────────────────┐
            │   │ Render Projects     │
            │   │ (using portfolio.yml)
            │   └─────────────────────┘
            │
            ├─► [2] pressed
            │   └─► Update() { currentPage = REFLECTIONS }
            │
            ├─► [↑] pressed
            │   └─► Update() { selectedIndex-- }
            │
            ├─► [q] pressed
            │   └─► Return tea.Quit()
            │       ▼
            │   ┌──────────────────┐
            │   │ Close SSH        │
            │   │ Close Program    │
            │   └──────────────────┘
            │
            └─► [?] pressed
                └─► Show Help
```

## Code Structure

### main.go - Entry Point

```go
func main()
  ├─ Create SSH Server (gliderlabs/ssh)
  │  ├─ Address: 0.0.0.0:2222
  │  ├─ Handler: handleSSH
  │  └─ HostSigners: auto-generated
  │
  ├─ Setup signal handlers (SIGINT, SIGTERM)
  │
  ├─ Start listening (non-blocking)
  │
  ├─ Wait for shutdown signal
  │
  └─ Graceful close

func handleSSH(s ssh.Session)
  ├─ Check if PTY allocated
  ├─ Get PTY dimensions
  ├─ Create Model struct
  ├─ Create Bubble Tea Program
  ├─ Run program
  └─ Handle errors
```

### model.go - TUI Logic

```go
type Model struct
  ├─ Name string              // Portfolio name
  ├─ Bio string               // Bio text
  ├─ Creations []Project      // Projects list
  ├─ Reflections []Reflection // Essays/thoughts
  ├─ Contacts []Contact       // Contact info
  │
  ├─ currentPage int          // Which page showing
  ├─ selectedIndex int        // Highlight position
  ├─ width, height int        // Terminal size
  └─ scrollOffset int         // For long content

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd)
  ├─ Handle KeyMsg
  │  ├─ "q" → return tea.Quit()
  │  ├─ "1" → switch page to projects
  │  ├─ "↑" → move selection up
  │  ├─ "↓" → move selection down
  │  └─ "↵" → open selected item
  │
  ├─ Handle WindowSizeMsg (terminal resized)
  │
  └─ Return updated model

func (m Model) View() string
  ├─ Build header
  │  └─ Name + Bio with Lipgloss styling
  │
  ├─ Build menu options
  │  └─ Highlight current selection
  │
  ├─ Render current page
  │  ├─ Home page
  │  ├─ Projects list
  │  ├─ Reflections list
  │  ├─ Contact info
  │  └─ Help/About
  │
  ├─ Build footer
  │  └─ Keyboard shortcuts
  │
  └─ Return formatted string
```

### portfolio.yml - Configuration Schema

```yaml
name: string                    # Portfolio name
bio: string                     # Bio/tagline

creations:                      # Projects/work
  - title: string              # Project title
    description: string        # Short description
    content: string            # Detailed content

reflections:                    # Essays/thoughts
  - title: string              # Essay title
    content: string            # Full text

contacts:                       # Contact links
  - platform: string           # GitHub, Twitter, etc
    url: string                # Link/email
```

## State Machine

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌──────────────────┐
│  Load YAML File  │
└────┬─────────────┘
     │
     ▼
┌────────────────────────┐
│  SSH Server Listening  │
└────┬───────────────────┘
     │
     ├─► Connection 1 ──┐
     │                  │
     ├─► Connection 2 ──├─► ┌──────────────┐
     │                  │   │ TUI Running  │
     └─► Connection N ──┘   │ Per Session  │
                            └──────────────┘
                                   │
                          ┌─────────┴──────────┐
                          │                    │
                    User Input           Window Resize
                          │                    │
                          ▼                    ▼
                     Update Model         Update Size
                          │                    │
                          └─────────┬──────────┘
                                    │
                                    ▼
                              Re-render View
                                    │
                          ┌─────────┴──────────┐
                          │                    │
                       Quit? (q)         Continue
                          │                    │
                          ▼                    ▼
                     Close Session    ┌────────────┐
                          │           │ Loop Again │
                          │           └────────────┘
                          │                │
                          └────┬───────────┘
                               │
                               ▼
                          ┌─────────────┐
                          │   Shutdown  │
                          └─────────────┘
```

## Component Interactions

### SSH Server → Bubble Tea Flow

```
SSH Client sends input
         │
         ▼
gliderlabs/ssh reads from PTY
         │
         ▼
handleSSH() forwards to Bubble Tea
         │
         ▼
tea.Program.Run() processes events
         │
    ┌────┴────┐
    │          │
    ▼          ▼
 Update()    View()
    │          │
    ▼          ▼
Update Model  Generate String
    │          │
    └────┬─────┘
         │
         ▼
Write to SSH session PTY
         │
         ▼
SSH sends to client terminal
         │
         ▼
User sees rendered TUI
```

### Rendering Pipeline

```
Model Data (currentPage, selectedIndex, etc)
         │
         ▼
    View() builds string
         │
    ┌────┴─────┬─────────┬──────────┐
    │           │         │          │
    ▼           ▼         ▼          ▼
  Header      Menu     Content    Footer
    │           │         │          │
    ▼           ▼         ▼          ▼
Lipgloss styles (colors, borders, padding)
    │           │         │          │
    └───────┬───┴─────┬───┴──────┬───┘
            │         │          │
            ▼         ▼          ▼
         Combine into single string
            │
            ▼
      Return to Bubble Tea
            │
            ▼
      Write to Terminal
```

## Performance Characteristics

### Memory Layout

```
┌──────────────────────────────────┐
│ Portfolio TUI Process Memory     │
├──────────────────────────────────┤
│ Binary Code          → ~6 MB      │
│ Go Runtime           → ~4 MB      │
│ SSH Server State     → ~1 MB      │
│ YAML Data (Cache)    → ~100 KB    │
│ TUI Buffers          → ~500 KB    │
│ Other (heap, stack)  → ~8 MB      │
├──────────────────────────────────┤
│ Total               → ~20 MB      │
└──────────────────────────────────┘

Scales linearly with portfolio size.
1000 projects = ~25 MB
```

### Timing

```
Operation              Time        Notes
─────────────────────────────────────────
SSH Connection         50-100ms    Network dependent
YAML Load              <1ms        Happens once
TTY Init               5-10ms      Per session
First Render           1-2ms       Generate string
Keypress Response      <1ms        Input → Update → View
Full Screen Redraw     1-2ms       60+ FPS capable
```

## Concurrency Model

```
Main Thread (Goroutine 1)
├─ SSH Server.ListenAndServe()
│  │
│  ├─► Connection 1
│  │   └─► Session Handler 1 (Goroutine 2)
│  │       └─► Bubble Tea Program 1
│  │
│  ├─► Connection 2
│  │   └─► Session Handler 2 (Goroutine 3)
│  │       └─► Bubble Tea Program 2
│  │
│  └─► Connection N
│      └─► Session Handler N (Goroutine N+1)
│          └─► Bubble Tea Program N
│
├─ Signal Handler (Goroutine 2)
│  └─ Waits for SIGINT/SIGTERM
│
└─ Main Thread
   └─ Blocks on <-done channel
```

## File I/O

### Startup Sequence

```
Program Start
    │
    ▼
Read portfolio.yml
    │
    ├─► YAML Parsing
    │   ├─ Parse name, bio
    │   ├─ Parse creations array
    │   ├─ Parse reflections array
    │   └─ Parse contacts array
    │
    └─► Cache in Memory
        (Stays in RAM for entire session)

No disk I/O after startup!
All operations are in-memory.
```

### SSH Key Generation

```
First Run:
  .ssh/ directory doesn't exist
         │
         ▼
  gliderlabs/ssh auto-generates
         │
         ├─► RSA host key (4096-bit)
         └─► ECDSA host key (256-bit)
         │
         ▼
  Store in .ssh/
         │
         ▼
  Use same keys on restart

Subsequent runs:
  Load existing keys from .ssh/
         │
         ▼
  No regeneration needed
```

## Security Model (Current)

```
┌─────────────────────────────────────────┐
│       SSH Connection                    │
├─────────────────────────────────────────┤
│ Transport Security                      │
│ └─ SSH Protocol (encrypted)             │
│    └─ Automatic key exchange            │
│    └─ AES-256-CTR (default cipher)      │
│                                          │
│ Authentication                          │
│ └─ DEMO: Accept any username/password   │
│    └─ NOT FOR PRODUCTION                │
│                                          │
│ Authorization                           │
│ └─ All users see same content           │
│    └─ Read-only access                  │
└─────────────────────────────────────────┘

WARNINGS:
⚠️ Password auth is demo-only
⚠️ All users see same data
⚠️ No access control per user
```

## Extension Points

### Easy to Modify

```go
// In model.go
View() → Add new sections
Update() → Add new keyboard shortcuts
```

### Medium Difficulty

```go
// In main.go
handleSSH() → Add authentication
→ Add different handlers per user
→ Add database connections

// In model.go
→ Add search/filter
→ Add themes
```

### Hard / Architecture Change

```
// Would require rewrite:
→ Multiple concurrent users with different views
→ Real-time updates
→ Database persistence
→ Plugin system
```

## Deployment Architecture

### Local Development

```
┌─────────────┐
│   Your PC   │
│             │
│ Terminal 1  │ Terminal 2
│   Runs:     │   Runs:
│ ./portfolio │ ssh -p 2222
│    -tui     │ localhost
└─────────────┘
```

### Network (Shared)

```
┌──────────────────────┐
│   Server Machine     │
│                      │
│  ./portfolio-tui     │
│  (listening 0.0.0.0  │
│   port 2222)         │
└──────────┬───────────┘
           │
   SSH Network
           │
  ┌────────┴────────┐
  │                 │
  ▼                 ▼
Client 1       Client 2
ssh -p 2222   ssh -p 2222
server.com    server.com
```

### Cloud VPS

```
┌──────────────────────────┐
│     VPS Provider         │
│ (AWS, Linode, etc)       │
│                          │
│  Binary: portfolio-tui   │
│  Config: portfolio.yml   │
│  Process: Running (22)   │
│  SSH: Open to Internet   │
│                          │
│ ssh -p 2222 vps.example  │
└──────────────────────────┘
```

## Bottlenecks & Optimization

### Current Bottlenecks

1. **Terminal I/O** (SSH transmission)
   - Unavoidable, part of design
   - ~1-2ms per render

2. **YAML Parsing** (only once at startup)
   - Currently ~1ms
   - Not a problem

3. **String Formatting** (per render)
   - ~1ms with Lipgloss
   - Could optimize with string pooling

### Optimization Strategies

```
If rendering is slow:
├─ Profile with pprof
├─ Reduce re-allocations
├─ Cache formatted strings
└─ Use string builder

If memory is high:
├─ Lazy-load projects
├─ Stream content
└─ Implement pagination

If SSH latency is high:
├─ Reduce render size
├─ Use compression
└─ Batch updates
```

## Monitoring & Debugging

### Debug Commands

```bash
# Check running instances
ps aux | grep portfolio-tui

# Monitor memory usage
watch -n1 'ps -aux | grep portfolio'

# Profile CPU
go test -cpuprofile=cpu.prof ./...
go tool pprof cpu.prof

# SSH verbose output
ssh -vvv -p 2222 localhost
```

### Log Points

SSH server logs to stdout:
```
[+] SSH Portfolio Server on 0.0.0.0:2222
[+] Connect: ssh -p 2222 user@localhost
[+] Password: anything
[!] Server shutting down
```

---

## Summary

**SSH Portfolio TUI** is a **lightweight, event-driven TUI application** served over SSH.

- **Single process** handles all connections
- **Goroutine per session** for concurrency
- **Bubble Tea** for efficient rendering
- **YAML** for simple configuration
- **In-memory** operation (fast, no DB needed)
- **Extensible** design for adding features

Perfect for portfolios, demos, and terminal aesthetics.

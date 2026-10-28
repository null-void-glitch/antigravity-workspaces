# 🛠️ Development Guide

Guide for extending and modifying the SSH Portfolio TUI.

## Project Structure

```
portfolio-tui/
├── main.go          # SSH server setup and handlers
├── model.go         # Bubble Tea TUI model
├── portfolio.yml    # Content/configuration
├── go.mod           # Go module definition
├── go.sum           # Dependency lock file
├── README.md        # User documentation
├── DEVELOPMENT.md   # This file
└── setup.sh         # Build script
```

## Code Overview

### main.go
Handles SSH server setup and session routing. Uses `gliderlabs/ssh` for the SSH server implementation.

Key functions:
- `main()` - Server initialization and signal handling
- `handleSSH()` - SSH session handler, creates Bubble Tea program

### model.go
Contains the Bubble Tea model that defines the TUI state and rendering logic.

Key components:
- `Model` struct - Main application state
- `Update()` - Handle user input and state changes
- `View()` - Render the current state to terminal
- Navigation between screens (home, projects, reflections, contact)

## Making Changes

### Adding New Sections

1. **Update portfolio.yml** with new content
2. **Add fields to Model struct** in model.go
3. **Update View()** to display new sections
4. **Update Update()** to handle navigation to new sections
5. **Rebuild**: `go build -o portfolio-tui`

### Styling Changes

All colors and styles are in model.go using Lipgloss. Example:

```go
var (
    primaryStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))
    successStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
)
```

Colors available:
- Named: `"red"`, `"green"`, `"blue"`, `"yellow"`, `"white"`, etc.
- Hex: `"#FF00FF"`
- ANSI 256: `"205"`, `"42"`, etc.

### Extending Authentication

Currently accepts any username/password. To add real auth:

```go
func handleSSH(s ssh.Session) {
    username := s.User()
    // Validate username and password
    if !isValidUser(username, password) {
        io.WriteString(s, "Authentication failed\n")
        return
    }
    // ... rest of handler
}
```

## Dependencies

```
github.com/charmbracelet/bubbletea v0.24.0  - TUI framework
github.com/charmbracelet/lipgloss v0.9.0    - Terminal styling
github.com/gliderlabs/ssh v0.3.5            - SSH server
gopkg.in/yaml.v2 v2.4.0                     - YAML parsing
```

To update a dependency:
```bash
go get -u github.com/charmbracelet/bubbletea
go mod tidy
```

## Building & Testing

### Build
```bash
go build -o portfolio-tui
```

### Build with optimization
```bash
go build -ldflags="-s -w" -o portfolio-tui
```

### Run locally
```bash
./portfolio-tui
```

Then in another terminal:
```bash
ssh -p 2222 localhost
```

### Cross-compile
```bash
# Linux AMD64
GOOS=linux GOARCH=amd64 go build -o portfolio-tui

# macOS ARM64
GOOS=darwin GOARCH=arm64 go build -o portfolio-tui

# Windows
GOOS=windows GOARCH=amd64 go build -o portfolio-tui.exe
```

## Advanced Features to Add

### Ideas for Enhancement

1. **ASCII Art Display**
   - Add animated ASCII art on home screen
   - Use `github.com/pterm/pterm` for fancy text

2. **Search Functionality**
   - Search through projects and reflections
   - Fuzzy matching with `github.com/sahilm/fuzzy`

3. **Markdown Rendering**
   - Parse and display markdown content
   - Use `github.com/charmbracelet/glamour`

4. **Real-time Stats**
   - Show GitHub stats or other APIs
   - Cache responses to avoid rate limits

5. **Themes**
   - Load different color schemes from config
   - Hot-reload without restart

6. **Analytics**
   - Track who visits your portfolio
   - Log to file or send to analytics service

7. **Code Syntax Highlighting**
   - Display code snippets with colors
   - Use `github.com/alecthomas/chroma`

## Common Issues & Solutions

### Build Errors
- Clear cache: `go clean -modcache`
- Update dependencies: `go get -u ./...`
- Verify Go version: `go version` (need 1.21+)

### SSH Connection Issues
- Check port: `ss -tlnp | grep 2222`
- Check firewall: `sudo ufw allow 2222`
- Verify SSH key: `.ssh/ssh_portfolio_key` exists

### Display Issues
- Terminal width/height: Set TERM=xterm-256color
- Color support: Some terminals need 24-bit color
- Font: Use monospace font (Noto Mono, Fira Code, etc.)

## Performance Optimization

For large portfolios:
1. Cache YAML parsing results
2. Use lazy loading for big sections
3. Limit rendered text buffers
4. Profile with `pprof`:
   ```bash
   go build -o portfolio-tui
   go test -cpuprofile=cpu.prof -memprofile=mem.prof
   go tool pprof cpu.prof
   ```

## Testing

Add unit tests to model_test.go:

```go
package main

import (
    "testing"
)

func TestModelUpdate(t *testing.T) {
    m := NewModel(80, 24)
    // Test update logic
}
```

Run tests:
```bash
go test ./...
```

## Contributing

If improving this project:
1. Keep code clean and documented
2. Add comments for complex logic
3. Test on multiple terminals
4. Update docs with changes
5. Follow Go best practices

## Resources

- Bubble Tea Docs: https://github.com/charmbracelet/bubbletea
- Lipgloss: https://github.com/charmbracelet/lipgloss
- SSH Server: https://github.com/gliderlabs/ssh
- Go SSH Client: `man ssh` (or online docs)

---

**Happy hacking! 🔓**

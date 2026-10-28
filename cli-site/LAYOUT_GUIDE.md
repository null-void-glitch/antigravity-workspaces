# Two-Column Layout Guide

## Current Structure (What You Have Now)
```
Banner (full width)
Bio Panel (full width)
Menu (full width)
Content (full width)
```

## New Structure (What You Want)
```
┌─────────────────────────┬──────────────────────┐
│  Large ASCII Art        │  Small ASCII Art     │
│  (Left Column)          │  (Top Right)         │
├─────────────────────────┤                      │
│                         │  Bio Text            │
│  (Still Left Column)    │  (Right Column)      │
│                         │                      │
└─────────────────────────┴──────────────────────┘
Menu & Content (Full Width Below)
```

## Code Changes to Make

### 1. Update the View() function in model.go

**Find this section (around line 145-165):**
```go
// Banner
banner := `
	Test
`
b.WriteString(banner)
b.WriteString("\n")

// Bio panel
bioStyle := lipgloss.NewStyle().
    Border(lipgloss.RoundedBorder()).
    BorderForeground(lipgloss.Color("6")).
    Padding(1, 2).
    Width(m.width - 4)

bioPanel := bioStyle.Render(m.content.Bio)
```

**Replace it with this:**
```go
// Calculate column widths
leftColWidth := m.width / 2 - 2      // ~50% minus padding
rightColWidth := m.width / 2 - 2     // ~50% minus padding

// LEFT COLUMN: Large Banner
largeBanner := `
████████████████████████████
█                          █
█     Your ASCII Art       █
█     (Big Banner)         █
█                          █
████████████████████████████
`

leftStyle := lipgloss.NewStyle().
    Width(leftColWidth).
    Height(20)

leftColumn := leftStyle.Render(largeBanner)

// RIGHT COLUMN: Small ASCII + Bio
smallBanner := `
  ◇
 /_/_\
/_/◇\_\
`

smallStyle := lipgloss.NewStyle().
    Align(lipgloss.Center).
    Width(rightColWidth)

bioStyle := lipgloss.NewStyle().
    Padding(1, 2).
    Width(rightColWidth)

rightTop := smallStyle.Render(smallBanner)
rightBottom := bioStyle.Render(m.content.Bio)
rightColumn := lipgloss.JoinVertical(
    lipgloss.Top,
    rightTop,
    rightBottom,
)

// COMBINE LEFT AND RIGHT (Side by side)
topSection := lipgloss.JoinHorizontal(
    lipgloss.Top,
    leftColumn,
    rightColumn,
)

b.WriteString(topSection)
b.WriteString("\n\n")
```

---

## Key Lipgloss Functions Explained

### `JoinHorizontal(align, left, right)`
Puts two strings side by side
```go
lipgloss.JoinHorizontal(lipgloss.Top, col1, col2)
// Result: col1 | col2 (aligned at top)
```

### `JoinVertical(align, top, bottom)`
Stacks two strings vertically
```go
lipgloss.JoinVertical(lipgloss.Top, top, bottom)
// Result:
//   top
//   bottom
```

### `Width()` and `Height()`
Control dimensions
```go
style := lipgloss.NewStyle().
    Width(40).      // 40 characters wide
    Height(20)      // 20 lines tall
```

---

## Complete Example

Here's a minimal working example:

```go
func (m Model) View() string {
    var b strings.Builder

    // Get available width
    w := m.width
    colWidth := w/2 - 2

    // LEFT: Large banner
    left := `
████████████████
█ Your ASCII    █
█ Art Here      █
████████████████
`
    leftStyle := lipgloss.NewStyle().
        Width(colWidth).
        Padding(0, 1)
    
    leftRendered := leftStyle.Render(left)

    // RIGHT: Small banner + Bio
    smallBanner := `
  ◇
 / \
/_____\
`
    smallStyle := lipgloss.NewStyle().
        Align(lipgloss.Center).
        Width(colWidth)
    
    bioStyle := lipgloss.NewStyle().
        Padding(1, 1).
        Width(colWidth)
    
    rightTop := smallStyle.Render(smallBanner)
    rightBottom := bioStyle.Render(m.content.Bio)
    rightRendered := lipgloss.JoinVertical(
        lipgloss.Top,
        rightTop,
        rightBottom,
    )

    // COMBINE (Side by side)
    topSection := lipgloss.JoinHorizontal(
        lipgloss.Top,
        leftRendered,
        rightRendered,
    )

    b.WriteString(topSection)
    b.WriteString("\n\n")

    // REST OF LAYOUT (Menu, etc) below...
    // ... (keep your existing menu code)

    return b.String()
}
```

---

## Tips for Your Layout

### 1. ASCII Art Sizing
- **Left banner:** Can be 20-25 lines tall, ~30 chars wide
- **Right banner:** Small, ~10 lines, ~15 chars wide

### 2. Column Width Calculation
```go
leftColWidth := m.width / 2 - 2    // Subtract 2 for padding
rightColWidth := m.width / 2 - 2
```

### 3. Vertical Alignment
Use `lipgloss.Top`, `lipgloss.Center`, or `lipgloss.Bottom`
```go
lipgloss.JoinHorizontal(lipgloss.Top, left, right)
// Both columns align at the top
```

### 4. Adding Borders
```go
style := lipgloss.NewStyle().
    Border(lipgloss.RoundedBorder()).
    BorderForeground(lipgloss.Color("6"))
```

### 5. Colors for ASCII Art
```go
asciiStyle := lipgloss.NewStyle().
    Foreground(lipgloss.Color("3"))  // Yellow

asciiRendered := asciiStyle.Render(asciiArt)
```

---

## Full View() Function Template

```go
func (m Model) View() string {
    var b strings.Builder

    // Column widths
    colWidth := m.width/2 - 2

    // ============ TOP SECTION (Two columns) ============
    
    // LEFT: Large banner
    leftBanner := `your large ASCII art here`
    leftStyle := lipgloss.NewStyle().
        Width(colWidth).
        Foreground(lipgloss.Color("6"))
    left := leftStyle.Render(leftBanner)

    // RIGHT: Small banner + bio
    smallBanner := `small ASCII art`
    bio := m.content.Bio
    
    smallStyle := lipgloss.NewStyle().
        Align(lipgloss.Center).
        Width(colWidth)
    bioStyle := lipgloss.NewStyle().
        Padding(1, 1).
        Width(colWidth)
    
    right := lipgloss.JoinVertical(
        lipgloss.Top,
        smallStyle.Render(smallBanner),
        bioStyle.Render(bio),
    )

    // Combine columns
    topSection := lipgloss.JoinHorizontal(
        lipgloss.Top,
        left,
        right,
    )
    b.WriteString(topSection)
    b.WriteString("\n\n")

    // ============ MENU SECTION (Full width) ============
    
    menuStr := ""
    for i, item := range m.menuItems {
        if i == m.selected {
            menuStr += lipgloss.NewStyle().
                Foreground(lipgloss.Color("2")).
                Bold(true).
                Render("◆ " + item)
        } else {
            menuStr += lipgloss.NewStyle().
                Render("◇ " + item)
        }
        if i < len(m.menuItems)-1 {
            menuStr += "    "
        }
    }
    b.WriteString(menuStr)
    b.WriteString("\n\n")

    // ============ CONTENT SECTION (Full width) ============
    
    contentStyle := lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(lipgloss.Color("6")).
        Padding(1, 2).
        Width(m.width - 4)
    
    b.WriteString(contentStyle.Render(m.content.Pages[m.page]))
    b.WriteString("\n")

    // ============ HELP TEXT (Full width) ============
    
    helpStyle := lipgloss.NewStyle().
        Foreground(lipgloss.Color("8"))
    
    b.WriteString(helpStyle.Render("[←→ to select • enter to open • q to quit]"))

    return b.String()
}
```

---

## What to Replace in Your model.go

Look for the `View()` function and replace the banner + bio section with the two-column layout above.

Keep everything else the same!


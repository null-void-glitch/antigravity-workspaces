package main

import (
	_ "embed"
	"fmt"
	"os"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"gopkg.in/yaml.v2"
)

//go:embed leftart.txt
var largeBanner string

type Menu string

const (
	MainMenu     Menu = "main"
	CreationMenu Menu = "things i've done"
	ReflectMenu  Menu = "cool stuff from other people"
	ContactMenu  Menu = "contacts"
)

type Content struct {
	Name        string `yaml:"name"`
	Bio         string `yaml:"bio"`
	Creations   []Item `yaml:"creations"`
	Reflections []Item `yaml:"reflections"`
	Contacts    []Item `yaml:"contacts"`
}

type Item struct {
	Title       string `yaml:"title"`
	Description string `yaml:"description"`
	Content     string `yaml:"content"`
	Platform    string `yaml:"platform"`
	URL         string `yaml:"url"`
}

type Model struct {
	width       int
	height      int
	content     Content
	currentMenu Menu
	selected    int
	menuItems   []string
}

func NewModel(width, height int) *Model {
	m := &Model{
		width:       width,
		height:      height,
		currentMenu: MainMenu,
		selected:    0,
		menuItems:   []string{"Things i've done", "Cool stuff from other people", "Contacts"},
	}
	m.loadContent()
	return m
}

func (m *Model) loadContent() {
	data, err := os.ReadFile("portfolio.yml")
	if err != nil {
		m.content = Content{
			Name: "Your Portfolio",
			Bio:  "Creator & storyteller on the internet",
			Creations: []Item{
				{Title: "Project 1", Description: "Cool project"},
				{Title: "Project 2", Description: "Another cool project"},
			},
			Reflections: []Item{
				{Title: "Thought 1", Content: "Deep thoughts here..."},
			},
			Contacts: []Item{
				{Platform: "GitHub", URL: "https://github.com"},
			},
		}
		return
	}

	err = yaml.Unmarshal(data, &m.content)
	if err != nil {
		m.content.Name = "Error loading config"
	}
}

func (m Model) Init() tea.Cmd {
	return nil
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "q":
			if m.currentMenu == MainMenu {
				return m, tea.Quit
			}
			m.currentMenu = MainMenu
			m.selected = 0

		case "left", "h":
			if m.currentMenu == MainMenu {
				m.selected = (m.selected - 1 + len(m.menuItems)) % len(m.menuItems)
			}

		case "right", "l":
			if m.currentMenu == MainMenu {
				m.selected = (m.selected + 1) % len(m.menuItems)
			}

		case "up", "k":
			if m.currentMenu != MainMenu {
				itemCount := len(m.content.Creations)
				if m.currentMenu == ReflectMenu {
					itemCount = len(m.content.Reflections)
				} else if m.currentMenu == ContactMenu {
					itemCount = len(m.content.Contacts)
				}
				if itemCount > 0 {
					m.selected = (m.selected - 1 + itemCount) % itemCount
				}
			}

		case "down", "j":
			if m.currentMenu != MainMenu {
				itemCount := len(m.content.Creations)
				if m.currentMenu == ReflectMenu {
					itemCount = len(m.content.Reflections)
				} else if m.currentMenu == ContactMenu {
					itemCount = len(m.content.Contacts)
				}
				if itemCount > 0 {
					m.selected = (m.selected + 1) % itemCount
				}
			}

		case "enter":
			if m.currentMenu == MainMenu {
				switch m.selected {
				case 0:
					m.currentMenu = CreationMenu
				case 1:
					m.currentMenu = ReflectMenu
				case 2:
					m.currentMenu = ContactMenu
				}
				m.selected = 0
			}
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
	}
	return m, nil
}

func (m Model) View() string {
	switch m.currentMenu {
	case CreationMenu:
		return m.viewCreations()
	case ReflectMenu:
		return m.viewReflections()
	case ContactMenu:
		return m.viewContacts()
	default:
		return m.viewMain()
	}
}

func (m Model) viewMain() string {
	var b strings.Builder

	// RIGHT COLUMN
	smallBanner := `
 ███▄    █  ██▓ ██░ ██  ██▓ ██▓     ██▓  ██████ ▄▄▄█████▓
 ██ ▀█   █ ▓██▒▓██░ ██▒▓██▒▓██▒    ▓██▒▒██    ▒ ▓  ██▒ ▓▒
▓██  ▀█ ██▒▒██▒▒██▀▀██░▒██▒▒██░    ▒██▒░ ▓██▄   ▒ ▓██░ ▒░
▓██▒  ▐▌██▒░██░░▓█ ░██ ░██░▒██░    ░██░  ▒   ██▒░ ▓██▓ ░ 
▒██░   ▓██░░██░░▓█▒░██▓░██░░██████▒░██░▒██████▒▒  ▒██▒ ░ 
░ ▒░   ▒ ▒ ░▓   ▒ ░░▒░▒░▓  ░ ▒░▓  ░░▓  ▒ ▒▓▒ ▒ ░  ▒ ░░   
░ ░░   ░ ▒░ ▒ ░ ▒ ░▒░ ░ ▒ ░░ ░ ▒  ░ ▒ ░░ ░▒  ░ ░    ░    
   ░   ░ ░  ▒ ░ ░  ░░ ░ ▒ ░  ░ ░    ▒ ░░  ░  ░    ░      
         ░  ░   ░  ░  ░ ░      ░  ░ ░        ░           
                                                         
    █    ██ ▄▄▄█████▓ ▒█████   ██▓███   ██▓ ▄▄▄          
    ██  ▓██▒▓  ██▒ ▓▒▒██▒  ██▒▓██░  ██▒▓██▒▒████▄        
   ▓██  ▒██░▒ ▓██░ ▒░▒██░  ██▒▓██░ ██▓▒▒██▒▒██  ▀█▄      
   ▓▓█  ░██░░ ▓██▓ ░ ▒██   ██░▒██▄█▓▒ ▒░██░░██▄▄▄▄██     
   ▒▒█████▓   ▒██▒ ░ ░ ████▓▒░▒██▒ ░  ░░██░ ▓█   ▓██▒    
   ░▒▓▒ ▒ ▒   ▒ ░░   ░ ▒░▒░▒░ ▒▓▒░ ░  ░░▓   ▒▒   ▓▒█░    
   ░░▒░ ░ ░     ░      ░ ▒ ▒░ ░▒ ░      ▒ ░  ▒   ▒▒ ░    
    ░░░ ░ ░   ░      ░ ░ ░ ▒  ░░        ▒ ░  ░   ▒       
      ░                  ░ ░            ░        ░  ░    
  `

	bioStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("14"))

	descStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("7"))

	rightTop := bioStyle.Render(smallBanner)
	descStyle = descStyle.Width(50) // Prevent bio from wrapping infinitely
	rightBottom := descStyle.Render(m.content.Bio)

	// MENU
	menuStr := ""
	for i, item := range m.menuItems {
		if i == m.selected {
			selected := lipgloss.NewStyle().
				Foreground(lipgloss.Color("2")).
				Bold(true)
			menuStr += selected.Render("◆ " + item)
		} else {
			unselected := lipgloss.NewStyle().
				Foreground(lipgloss.Color("8"))
			menuStr += unselected.Render("◇ " + item)
		}
		if i < len(m.menuItems)-1 {
			menuStr += "    "
		}
	}
	menuBlock := lipgloss.NewStyle().MarginTop(2).Render(menuStr)

	// Join right column vertically
	rightCol := lipgloss.JoinVertical(lipgloss.Left, rightTop, rightBottom, menuBlock)

	maxH := m.height
	if maxH < 10 {
		maxH = 24
	}

	// Format left column (truncate braille to ~55 columns, crop height to terminal height)
	leftCol := lipgloss.NewStyle().Width(55).MaxWidth(55).MaxHeight(maxH - 5).Render(largeBanner)

	// Combine columns horizontally
	container := lipgloss.JoinHorizontal(lipgloss.Top, leftCol, lipgloss.NewStyle().MarginLeft(4).Render(rightCol))

	// Ensure the entire container does NOT exceed terminal bounds to prevent off-screen scrolling
	container = lipgloss.NewStyle().MaxHeight(maxH - 4).MaxWidth(m.width).Render(container)

	b.WriteString(container)
	b.WriteString("\n\n")

	// HELP
	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("8"))

	b.WriteString(helpStyle.Render("[←→ to select | enter to open | CTRL+click to open link | q to quit]"))

	return b.String()
}

func (m Model) viewCreations() string {
	var b strings.Builder

	titleStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("2")).
		Bold(true)

	b.WriteString(titleStyle.Render("◆ Things i've done") + "\n\n")

	for i, item := range m.content.Creations {
		if i == m.selected {
			selected := lipgloss.NewStyle().
				Foreground(lipgloss.Color("2")).
				Bold(true)
			b.WriteString(selected.Render("→ " + item.Title) + "\n")
		} else {
			unselected := lipgloss.NewStyle().
				Foreground(lipgloss.Color("7"))
			b.WriteString(unselected.Render("  " + item.Title) + "\n")
		}

		descStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("8"))
		
		descStr := item.Description
		if item.URL != "" {
			descStr += "\n   Link: " + makeLink(item.URL, item.URL)
		}
		
		b.WriteString(descStyle.Render("   " + descStr) + "\n\n")
	}

	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("8"))
	b.WriteString(helpStyle.Render("[↑↓ to navigate • q to go back]"))

	return b.String()
}

func (m Model) viewReflections() string {
	var b strings.Builder

	titleStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("3")).
		Bold(true)

	b.WriteString(titleStyle.Render("◆ Cool Stuff from other people") + "\n\n")

	for i, item := range m.content.Reflections {
		if i == m.selected {
			selected := lipgloss.NewStyle().
				Foreground(lipgloss.Color("3")).
				Bold(true)
			b.WriteString(selected.Render("→ " + item.Title) + "\n")
		} else {
			unselected := lipgloss.NewStyle().
				Foreground(lipgloss.Color("7"))
			b.WriteString(unselected.Render("  " + item.Title) + "\n")
		}

		contentStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("8"))
		
		displayStr := item.Content
		if item.URL != "" {
			if displayStr != "" {
				displayStr += "\n   "
			}
			displayStr += makeLink(item.URL, item.URL)
		}
		
		b.WriteString(contentStyle.Render("   " + displayStr) + "\n\n")
	}

	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("8"))
	b.WriteString(helpStyle.Render("[↑↓ to navigate | CTRL+click to follow links | q to go back]"))

	return b.String()
}

func (m Model) viewContacts() string {
	var b strings.Builder

	titleStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("5")).
		Bold(true)

	b.WriteString(titleStyle.Render("◆ Contacts") + "\n\n")

	for i, item := range m.content.Contacts {
		if i == m.selected {
			selected := lipgloss.NewStyle().
				Foreground(lipgloss.Color("5")).
				Bold(true)
			b.WriteString(selected.Render("→ " + item.Platform) + "\n")
		} else {
			unselected := lipgloss.NewStyle().
				Foreground(lipgloss.Color("7"))
			b.WriteString(unselected.Render("  " + item.Platform) + "\n")
		}

		urlStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("8"))
		b.WriteString(urlStyle.Render("   " + makeLink(item.URL, item.URL)) + "\n\n")
	}

	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("8"))
	b.WriteString(helpStyle.Render("[↑↓ to navigate | CTRL+click to follow links | q to go back]"))

	return b.String()
}

func padRight(s string, width int) string {
	sw := lipgloss.Width(s)
	if sw >= width {
		return truncateString(s, width)
	}
	return s + strings.Repeat(" ", width-sw)
}

func truncateString(s string, width int) string {
	var b strings.Builder
	currentWidth := 0
	for _, r := range s {
		rw := lipgloss.Width(string(r))
		if currentWidth+rw > width {
			break
		}
		b.WriteRune(r)
		currentWidth += rw
	}
	return b.String()
}

// makeLink turns a URL into a clickable terminal hyperlink using the OSC 8 ANSI sequence.
func makeLink(text, url string) string {
	if url == "" {
		return text
	}
	cleanURL := url
	if strings.HasPrefix(url, "Spotify: ") {
		cleanURL = strings.TrimPrefix(url, "Spotify: ")
	}
	if !strings.HasPrefix(cleanURL, "http") && strings.Contains(cleanURL, "@") && !strings.HasPrefix(cleanURL, "mailto:") && !strings.HasPrefix(cleanURL, "@") {
		cleanURL = "mailto:" + cleanURL
	}

	if strings.HasPrefix(cleanURL, "http") || strings.HasPrefix(cleanURL, "mailto:") {
		// OSC 8 escape sequence syntax: \033]8;;URL\033\TEXT\033]8;;\033\
		return fmt.Sprintf("\033]8;;%s\033\\%s\033]8;;\033\\", cleanURL, text)
	}
	return text
}

package main

import (
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"syscall"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/gliderlabs/ssh"
)

const (
	host = "0.0.0.0"
	port = 2222
)

func main() {
	s := &ssh.Server{
		Addr: fmt.Sprintf("%s:%d", host, port),
		Handler: handleSSH,
	}

	// This will generate the key if it doesn't exist, and load it
	ssh.HostKeyFile("ssh_host_ed25519_key")(s)

	done := make(chan os.Signal, 1)
	signal.Notify(done, syscall.SIGINT, syscall.SIGTERM)

	log.Printf("[+] SSH Portfolio Server on %s\n", s.Addr)
	log.Printf("[+] Connect: ssh -p %d user@localhost\n", port)
	log.Printf("[+] Password: anything\n")

	go func() {
		if err := s.ListenAndServe(); err != nil {
			log.Fatalln(err)
		}
	}()

	<-done
	log.Println("[!] Server shutting down")
	s.Close()
}

func handleSSH(s ssh.Session) {
	// Get PTY info
	pty, _, isPTY := s.Pty()
	if !isPTY {
		io.WriteString(s, "No PTY allocated\n")
		return
	}

	// Create model using actual PTY dimensions
	m := NewModel(pty.Window.Width, pty.Window.Height)
	
	// Create Bubble Tea program WITH alt screen + renderer
	p := tea.NewProgram(m, 
		tea.WithInput(s), 
		tea.WithOutput(s), 
		tea.WithAltScreen(),
		tea.WithMouseCellMotion())
	
	// Run program
	if _, err := p.Run(); err != nil {
		log.Printf("Error: %v\n", err)
	}
}

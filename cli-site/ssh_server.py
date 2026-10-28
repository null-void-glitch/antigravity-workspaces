#!/usr/bin/env python3
"""
SSH-based TUI Portfolio Site
Inspired by ssh.moriliu.com
"""

import paramiko
import socket
import threading
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import yaml
import io


class ChannelWriter:
    """Wrapper for writing to SSH channel"""
    def __init__(self, channel):
        self.channel = channel

    def write(self, text):
        if isinstance(text, str):
            text = text.encode('utf-8', errors='replace')
        try:
            self.channel.sendall(text)
        except:
            pass
        return len(text)

    def flush(self):
        pass

    def isatty(self):
        return True


class SSHServerInterface(paramiko.ServerInterface):
    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        return paramiko.OPEN_SUCCEEDED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return paramiko.OPEN_SUCCEEDED

    def check_channel_exec_request(self, channel, command):
        return paramiko.OPEN_SUCCEEDED


class PortfolioTUI:
    def __init__(self, channel):
        self.channel = channel
        self.channel.settimeout(0.05)
        self.writer = ChannelWriter(channel)
        self.console = Console(
            file=self.writer,
            force_terminal=True,
            width=100,
            legacy_windows=False
        )
        self.current_menu = "main"
        self.selected_index = 0
        self.menu_items = {
            "main": ["Creations", "Reflections", "Contacts"],
        }
        self.load_content()

    def load_content(self):
        """Load portfolio content from config file"""
        config_path = Path(__file__).parent / "portfolio.yml"
        if config_path.exists():
            with open(config_path) as f:
                self.content = yaml.safe_load(f) or {}
        else:
            self.content = {
                "name": "Your Name",
                "bio": "Creator & Developer",
                "creations": [
                    {"title": "Project 1", "description": "Cool project"},
                    {"title": "Project 2", "description": "Another cool project"},
                ],
                "reflections": [
                    {"title": "Thought 1", "content": "Deep thoughts here..."},
                ],
                "contacts": [
                    {"platform": "GitHub", "url": "https://github.com"},
                    {"platform": "Twitter", "url": "https://twitter.com"},
                ],
            }

    def clear_screen(self):
        """Clear screen using ANSI codes"""
        self.writer.write("\033[2J\033[H")

    def render_banner(self):
        """Render the welcome banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                      🌙 Welcome to My Portfolio 🌙                           ║
║                                                                              ║
║                      Explore · Create · Reflect                              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        self.console.print(banner)

    def render_menu(self):
        """Render the main menu"""
        self.clear_screen()
        self.render_banner()

        # Bio section
        bio_text = self.content.get("bio", "Creator & storyteller")
        bio_panel = Panel(
            bio_text,
            title=f"[bold cyan]{self.content.get('name', 'Your Name')}[/bold cyan]",
            border_style="cyan",
        )
        self.console.print(bio_panel)
        self.console.print()

        # Menu items
        for i, item in enumerate(self.menu_items["main"]):
            if i == self.selected_index:
                self.console.print(f"  [bold green]→ {item} ←[/bold green]")
            else:
                self.console.print(f"    {item}")

        self.console.print()
        self.console.print("[dim][← → to select · enter to open · q to quit][/dim]")
        self.console.print()

    def render_creations(self):
        """Display creations section"""
        self.clear_screen()
        self.console.print("[bold cyan]≡ Creations[/bold cyan]\n")

        creations = self.content.get("creations", [])
        if creations:
            for item in creations:
                panel = Panel(
                    item.get("description", ""),
                    title=item.get("title", "Untitled"),
                    border_style="green",
                )
                self.console.print(panel)
                self.console.print()
        else:
            self.console.print("[yellow]No creations yet...[/yellow]\n")

        self.console.print("[dim][q to go back][/dim]")

    def render_reflections(self):
        """Display reflections section"""
        self.clear_screen()
        self.console.print("[bold cyan]≡ Reflections[/bold cyan]\n")

        reflections = self.content.get("reflections", [])
        if reflections:
            for item in reflections:
                panel = Panel(
                    item.get("content", ""),
                    title=item.get("title", "Untitled"),
                    border_style="yellow",
                )
                self.console.print(panel)
                self.console.print()
        else:
            self.console.print("[yellow]No reflections yet...[/yellow]\n")

        self.console.print("[dim][q to go back][/dim]")

    def render_contacts(self):
        """Display contacts section"""
        self.clear_screen()
        self.console.print("[bold cyan]≡ Contacts[/bold cyan]\n")

        contacts = self.content.get("contacts", [])
        if contacts:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Platform")
            table.add_column("URL")

            for item in contacts:
                table.add_row(
                    item.get("platform", ""),
                    item.get("url", "")
                )

            self.console.print(table)
        else:
            self.console.print("[yellow]No contacts yet...[/yellow]")

        self.console.print()
        self.console.print("[dim][q to go back][/dim]")

    def read_key(self):
        """Read a keypress, handling multi-byte escape sequences for arrow keys."""
        data = self.channel.recv(1)
        if not data:
            return None
        char = data.decode('utf-8', errors='ignore')

        # Detect escape sequence
        if char == '\x1b':
            try:
                seq1 = self.channel.recv(1)
                if not seq1:
                    return 'escape'
                seq2 = self.channel.recv(1)
                if not seq2:
                    return 'escape'
                code = seq1.decode('utf-8', errors='ignore') + seq2.decode('utf-8', errors='ignore')
                arrow_map = {'[A': 'up', '[B': 'down', '[C': 'right', '[D': 'left'}
                return arrow_map.get(code, 'escape')
            except socket.timeout:
                return 'escape'

        return char

    def handle_key(self, key):
        """Handle a parsed key input"""
        if key in ("q", "Q"):
            if self.current_menu == "main":
                return False  # Exit
            else:
                self.current_menu = "main"
                self.selected_index = 0
                self.render_menu()
                return True
        
        if self.current_menu == "main":
            if key in ("right", "d"):
                self.selected_index = (self.selected_index + 1) % len(self.menu_items["main"])
                self.render_menu()
            elif key in ("left", "a"):
                self.selected_index = (self.selected_index - 1) % len(self.menu_items["main"])
                self.render_menu()
            elif key in ("\r", "\n"):
                menu_name = self.menu_items["main"][self.selected_index].lower()
                self.selected_index = 0
                if menu_name == "creations":
                    self.current_menu = "creations"
                    self.render_creations()
                elif menu_name == "reflections":
                    self.current_menu = "reflections"
                    self.render_reflections()
                elif menu_name == "contacts":
                    self.current_menu = "contacts"
                    self.render_contacts()
        return True

    def run(self):
        """Main event loop"""
        self.render_menu()

        try:
            while True:
                try:
                    key = self.read_key()
                    if key is None:
                        break
                    if key:
                        result = self.handle_key(key)
                        if not result:
                            break
                
                except socket.timeout:
                    # No data available, that's fine
                    continue
                except Exception as e:
                    # Connection issue
                    break

        except Exception as e:
            pass
        finally:
            try:
                self.channel.close()
            except:
                pass


def handle_client(client, addr, host_key):
    """Handle an individual client connection"""
    try:
        transport = paramiko.Transport(client)
        transport.add_server_key(host_key)

        server = SSHServerInterface()
        transport.start_server(server=server)

        # Accept channel
        channel = transport.accept(20)
        if channel is None:
            print(f"[!] No channel from {addr}")
            transport.close()
            return

        print(f"[+] Channel opened from {addr}")

        # Run TUI
        tui = PortfolioTUI(channel)
        tui.run()

        transport.close()

    except Exception as e:
        print(f"[!] Client error {addr}: {e}")
        import traceback
        traceback.print_exc()
        try:
            client.close()
        except:
            pass


def start_ssh_server(port=2222, host="0.0.0.0"):
    """Start the SSH server"""
    # Generate/load host key
    key_path = Path.home() / ".ssh" / "ssh_portfolio_key"
    key_path.parent.mkdir(parents=True, exist_ok=True)

    if key_path.exists():
        print(f"[+] Loading host key")
        host_key = paramiko.RSAKey.from_private_key_file(str(key_path))
    else:
        print(f"[*] Generating host key...")
        host_key = paramiko.RSAKey.generate(2048)
        host_key.write_private_key_file(str(key_path))
        os.chmod(key_path, 0o600)

    # Create listening socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(100)

    print(f"[+] SSH Portfolio Server on {host}:{port}")
    print(f"[+] Connect: ssh -p 2222 user@localhost")
    print(f"[+] Password: anything\n")

    try:
        while True:
            client, addr = sock.accept()
            print(f"[*] Connection from {addr}")
            t = threading.Thread(
                target=handle_client,
                args=(client, addr, host_key),
                daemon=True
            )
            t.start()
    except KeyboardInterrupt:
        print("\n[!] Server shutting down")
    finally:
        sock.close()


if __name__ == "__main__":
    start_ssh_server(port=2222)

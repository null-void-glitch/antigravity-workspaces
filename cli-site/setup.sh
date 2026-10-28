#!/bin/bash
# SSH Portfolio TUI Setup Script

set -e

echo "🌙 SSH Portfolio TUI Setup"
echo "=========================="
echo ""

# Check if Go is installed
if ! command -v go &> /dev/null; then
    echo "❌ Go is not installed. Please install Go 1.21 or higher."
    exit 1
fi

echo "✅ Go is installed: $(go version)"
echo ""

# Build the project
echo "📦 Building portfolio-tui..."
go mod download
go mod tidy
go build -o portfolio-tui

echo "✅ Build successful!"
echo ""

# Create .ssh directory if it doesn't exist
mkdir -p .ssh
echo "✅ .ssh directory ready"
echo ""

# Show next steps
echo "🚀 Setup complete! Next steps:"
echo ""
echo "1. Edit portfolio.yml with your information"
echo "2. Run the server:"
echo "   ./portfolio-tui"
echo ""
echo "3. Connect in another terminal:"
echo "   ssh -p 2222 user@localhost"
echo ""
echo "Any username/password works!"
echo ""

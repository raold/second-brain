#!/bin/bash

echo "Opening Second Brain Interfaces..."
echo ""

# Function to open URL in browser
open_browser() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux (including WSL)
        if command -v xdg-open > /dev/null; then
            xdg-open "$1"
        elif command -v wslview > /dev/null; then
            # WSL specific
            wslview "$1"
        elif [[ -n "$WSL_DISTRO_NAME" ]]; then
            # WSL fallback to Windows
            cmd.exe /c start "$1"
        else
            echo "Please open manually: $1"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "$1"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Windows
        start "$1"
    fi
}

# Open Swagger UI
echo "1. Opening Swagger UI (API Docs)..."
open_browser "http://localhost:8001/docs"

# Open Dashboard
echo "2. Opening Dashboard..."
open_browser "file:///mnt/c/tools/second-brain/dashboard.html"

echo ""
echo "✅ Interfaces opened!"
echo ""
echo "Available at:"
echo "  - Swagger API Docs: http://localhost:8001/docs"
echo "  - Dashboard: file:///mnt/c/tools/second-brain/dashboard.html"
echo "  - Simple UI: file:///mnt/c/tools/second-brain/simple_ui.html"
echo ""
echo "If they didn't open automatically, copy and paste the URLs above into your browser."
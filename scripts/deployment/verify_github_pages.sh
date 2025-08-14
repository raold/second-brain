#!/bin/bash

echo "🔍 GitHub Pages Verification Script"
echo "===================================="
echo ""

# Check if docs folder exists
if [ -d "docs" ]; then
    echo "✅ docs/ folder exists"
else
    echo "❌ docs/ folder not found"
    exit 1
fi

# Check for required files
required_files=("docs/index.html" "docs/interface.html" "docs/openapi.json" "docs/.nojekyll")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

echo ""
echo "📝 GitHub Pages Configuration Instructions:"
echo "==========================================="
echo "1. Go to: https://github.com/raold/second-brain/settings/pages"
echo "2. Under 'Source', select:"
echo "   - Branch: main"
echo "   - Folder: /docs"
echo "3. Click 'Save'"
echo "4. Wait 2-5 minutes for deployment"
echo "5. Visit: https://raold.github.io/second-brain/"
echo ""
echo "🧪 Test locally with:"
echo "   python3 -m http.server 8082 --directory docs"
echo "   Then open: http://localhost:8082/"
echo ""

# Test local server
if command -v python3 &> /dev/null; then
    echo "💡 Would you like to test locally now? (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        echo "Starting local server on http://localhost:8082/"
        echo "Press Ctrl+C to stop"
        python3 -m http.server 8082 --directory docs
    fi
fi
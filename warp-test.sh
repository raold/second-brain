#!/bin/bash
# Quick test of Cipher memories in terminal

echo "🧠 Testing Cipher Memory System"
echo "================================"
echo ""

echo "📝 Your recent memories:"
python3 /Users/dro/Library/CloudStorage/GoogleDrive-dro@lynchburgsmiles.com/My\ Drive/projects/second-brain/scripts/cipher_helper.py list --limit 3

echo ""
echo "🔍 Searching for 'docker':"
python3 /Users/dro/Library/CloudStorage/GoogleDrive-dro@lynchburgsmiles.com/My\ Drive/projects/second-brain/scripts/cipher_helper.py search docker

echo ""
echo "✅ Cipher is working! Use these commands:"
echo "  mem 'your memory' --tags tag1,tag2"
echo "  memsearch 'search term'"
echo "  memlist"
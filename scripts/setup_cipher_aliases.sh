#!/bin/bash
# Setup Cipher aliases for easy memory management

SCRIPT_PATH="/Users/dro/Library/CloudStorage/GoogleDrive-dro@lynchburgsmiles.com/My Drive/projects/second-brain/scripts/cipher_helper.py"

# Detect shell
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.profile"
fi

# Add aliases
echo "" >> "$SHELL_RC"
echo "# Cipher Memory Aliases" >> "$SHELL_RC"
echo "alias mem='python3 \"$SCRIPT_PATH\" add'" >> "$SHELL_RC"
echo "alias memsearch='python3 \"$SCRIPT_PATH\" search'" >> "$SHELL_RC"
echo "alias memlist='python3 \"$SCRIPT_PATH\" list'" >> "$SHELL_RC"
echo "alias memexport='python3 \"$SCRIPT_PATH\" export'" >> "$SHELL_RC"
echo "" >> "$SHELL_RC"

echo "✅ Aliases added to $SHELL_RC"
echo ""
echo "Now you can use:"
echo "  mem 'your memory here' --tags tag1,tag2"
echo "  memsearch 'search term'"
echo "  memlist"
echo "  memexport --format markdown"
echo ""
echo "Run: source $SHELL_RC"
#!/bin/bash
# Shell utility functions for second-brain development

# =============================================================================
# Python Development Utilities
# =============================================================================

# workon DIR  → activate (or create) a venv in DIR/.venv
workon() {
  local target=${1:-.}
  if [ ! -d "$target/.venv" ]; then
    python -m venv "$target/.venv"
  fi
  source "$target/.venv/bin/activate"
}

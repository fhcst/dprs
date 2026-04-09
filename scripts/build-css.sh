#!/usr/bin/env bash
# Build Tailwind CSS from templates using the Standalone CLI.
# Usage:
#   ./scripts/build-css.sh          # one-time build (minified)
#   ./scripts/build-css.sh --watch  # watch mode for development

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TAILWIND="$PROJECT_ROOT/tools/tailwindcss"
INPUT="$PROJECT_ROOT/src/static/css/input.css"
OUTPUT="$PROJECT_ROOT/src/static/css/tailwind.css"

if [ ! -x "$TAILWIND" ]; then
  echo "Error: Tailwind CLI not found at $TAILWIND"
  echo "Download it with:"
  echo "  curl -sL https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m) -o $TAILWIND && chmod +x $TAILWIND"
  exit 1
fi

if [ "${1:-}" = "--watch" ]; then
  echo "Watching for changes..."
  "$TAILWIND" --input "$INPUT" --output "$OUTPUT" --watch
else
  echo "Building CSS..."
  "$TAILWIND" --input "$INPUT" --output "$OUTPUT" --minify
  echo "Done: $OUTPUT ($(wc -c < "$OUTPUT" | tr -d ' ') bytes)"
fi

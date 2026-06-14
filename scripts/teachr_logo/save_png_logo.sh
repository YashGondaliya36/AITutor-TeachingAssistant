#!/bin/bash

# Script to convert logo SVG files to PNG format
# Usage: ./save_png_logo.sh

# Set paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Output directory
OUTPUT_DIR="$PROJECT_ROOT"

# Convert dark logo (black text, transparent background)
if [ -f "$PROJECT_ROOT/logo.svg" ]; then
    echo "Converting logo.svg to logo.png (540x140)..."
    rsvg-convert "$PROJECT_ROOT/logo.svg" -w 540 -h 140 -o "$OUTPUT_DIR/logo.png"
    echo "✓ Created logo.png"
else
    echo "⚠ logo.svg not found"
fi

# Convert white logo (white text for dark backgrounds)
if [ -f "$PROJECT_ROOT/logo_white.svg" ]; then
    echo "Converting logo_white.svg to logo_white.png (540x140)..."
    rsvg-convert "$PROJECT_ROOT/logo_white.svg" -w 540 -h 140 -o "$OUTPUT_DIR/logo_white.png"
    echo "✓ Created logo_white.png"
else
    echo "⚠ logo_white.svg not found"
fi

echo ""
echo "Done! PNG files saved to: $OUTPUT_DIR"

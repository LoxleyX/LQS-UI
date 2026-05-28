#!/bin/bash
# Export all LQS addon data from server files.
# Run this after updating quest/content files.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Exporting quest data ==="
python3 "$SCRIPT_DIR/export-quests.py"

echo ""
echo "=== Exporting dragonslaying ==="
python3 "$SCRIPT_DIR/export-dragonslaying.py"

echo ""
echo "=== Exporting incursion ==="
python3 "$SCRIPT_DIR/export-incursion.py"

echo ""
echo "=== Done ==="

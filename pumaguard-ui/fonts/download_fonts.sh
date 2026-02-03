#!/bin/bash
set -e

# Script to download Google Fonts for PumaGuard UI offline use
# Fonts are licensed under Apache License 2.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Downloading fonts for PumaGuard UI..."

# Base URL for Google Fonts GitHub repo
ROBOTO_BASE="https://github.com/google/roboto/raw/main/src/hinted"
ROBOTO_MONO_BASE="https://github.com/googlefonts/RobotoMono/raw/main/fonts/ttf"

# Download Roboto fonts
echo "Downloading Roboto Regular..."
curl -L "$ROBOTO_BASE/Roboto-Regular.ttf" -o Roboto-Regular.ttf

echo "Downloading Roboto Medium..."
curl -L "$ROBOTO_BASE/Roboto-Medium.ttf" -o Roboto-Medium.ttf

echo "Downloading Roboto Bold..."
curl -L "$ROBOTO_BASE/Roboto-Bold.ttf" -o Roboto-Bold.ttf

echo "Downloading Roboto Light..."
curl -L "$ROBOTO_BASE/Roboto-Light.ttf" -o Roboto-Light.ttf

# Download Roboto Mono fonts
echo "Downloading Roboto Mono Regular..."
curl -L "$ROBOTO_MONO_BASE/RobotoMono-Regular.ttf" -o RobotoMono-Regular.ttf

echo "Downloading Roboto Mono Medium..."
curl -L "$ROBOTO_MONO_BASE/RobotoMono-Medium.ttf" -o RobotoMono-Medium.ttf

echo "Downloading Roboto Mono Bold..."
curl -L "$ROBOTO_MONO_BASE/RobotoMono-Bold.ttf" -o RobotoMono-Bold.ttf

# Check if we got all the files
EXPECTED_FILES=(
    "Roboto-Regular.ttf"
    "Roboto-Medium.ttf"
    "Roboto-Bold.ttf"
    "Roboto-Light.ttf"
    "RobotoMono-Regular.ttf"
    "RobotoMono-Medium.ttf"
    "RobotoMono-Bold.ttf"
)

MISSING_FILES=()
for file in "${EXPECTED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    echo ""
    echo "✓ All fonts downloaded successfully!"
    echo ""
    echo "Downloaded files:"
    ls -lh *.ttf
    echo ""
    echo "Next steps:"
    echo "1. Run 'flutter pub get' in the pumaguard-ui directory"
    echo "2. Rebuild the app with 'make build-ui'"
else
    echo ""
    echo "⚠ Warning: Some font files were not found:"
    printf '  - %s\n' "${MISSING_FILES[@]}"
    echo ""
    echo "You may need to download fonts manually from:"
    echo "- https://fonts.google.com/specimen/Roboto"
    echo "- https://fonts.google.com/specimen/Roboto+Mono"
    exit 1
fi

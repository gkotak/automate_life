#!/bin/bash

# Build script for Particles Chrome Extension
# Creates a distributable ZIP file

echo "🔨 Building Particles Chrome Extension..."
echo ""

# Check if icons exist
if [ ! -f "icons/icon-16.png" ] || [ ! -f "icons/icon-48.png" ] || [ ! -f "icons/icon-128.png" ]; then
    echo "⚠️  WARNING: Icon files are missing!"
    echo "   Please add icon-16.png, icon-48.png, and icon-128.png to the icons/ folder"
    echo "   See icons/icon-creation-instructions.txt for details"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create build directory
BUILD_DIR="build"
EXTENSION_NAME="particles-extension"
VERSION=$(grep '"version"' manifest.json | cut -d'"' -f4)
OUTPUT_FILE="${EXTENSION_NAME}-v${VERSION}.zip"

echo "📦 Creating build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/$EXTENSION_NAME"

# Copy extension files
echo "📋 Copying extension files..."
cp manifest.json "$BUILD_DIR/$EXTENSION_NAME/"
cp background.js "$BUILD_DIR/$EXTENSION_NAME/"
cp -r icons "$BUILD_DIR/$EXTENSION_NAME/"
cp -r sidepanel "$BUILD_DIR/$EXTENSION_NAME/"
cp -r lib "$BUILD_DIR/$EXTENSION_NAME/"

# Copy documentation
echo "📄 Adding documentation..."
cp README.md "$BUILD_DIR/$EXTENSION_NAME/"

# Create ZIP file
echo "🗜️  Creating ZIP archive..."
cd "$BUILD_DIR"
zip -r "../$OUTPUT_FILE" "$EXTENSION_NAME" -q

cd ..
rm -rf "$BUILD_DIR"

# Calculate file size
FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo ""
echo "✅ Build complete!"
echo ""
echo "📦 Package: $OUTPUT_FILE"
echo "📏 Size: $FILE_SIZE"
echo ""
echo "🚀 Distribution options:"
echo "   1. Share the ZIP file directly with users"
echo "   2. Upload to GitHub Releases"
echo "   3. Upload to Google Drive/Dropbox"
echo "   4. Submit to Chrome Web Store (requires developer account)"
echo ""
echo "📖 Installation instructions are included in the ZIP (README.md)"
echo ""

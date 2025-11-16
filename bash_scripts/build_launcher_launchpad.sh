#!/bin/bash
set -e

echo "Building LaunchPad..."

pwd

# Check if required files exist
if [ ! -f "launcher/LaunchPad.m" ]; then
    echo "Error: launcher/LaunchPad.m not found"
    exit 1
fi

if [ ! -d "frameworks/Sparkle-2.7.1/Sparkle.framework" ]; then
    echo "Error: frameworks/Sparkle-2.7.1/Sparkle.framework not found"
    exit 1
fi

# Compile the Objective-C launcher
echo "Compiling LaunchPad..."
clang -framework Cocoa \
      -framework Sparkle \
      -F ./frameworks/Sparkle-2.7.1/ \
      -rpath @executable_path/../Frameworks \
      -o LaunchPad \
      launcher/LaunchPad.m

# Optional: Sign the launcher (comment out if you don't have Developer ID)
# Uncomment and replace with your actual Developer ID when ready
# echo "Signing LaunchPad..."
# codesign --force --sign "Developer ID Application: Your Name (TEAMID)" LaunchPad

echo "LaunchPad built successfully!"
echo "LaunchPad executable created in project root"
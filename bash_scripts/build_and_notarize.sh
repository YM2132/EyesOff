#!/bin/bash

# Function to check if the previous command succeeded
check_status() {
  if [ $? -ne 0 ]; then
    echo "❌ Error: $1 failed"
    exit 1
  else
    echo "✅ Success: $1 completed"
  fi
}

# Clear terminal and show script start
clear
echo "==================================================="
echo "📦 Starting EyesOff build and notarization process"
echo "==================================================="

rm -rf build dist

# Step 0: Build with PyInstaller
echo "🔨 Step 0: Building with PyInstaller..."
pyinstaller EyesOff.spec
check_status "PyInstaller build"

id="Developer ID Application: Yusuf Mohammad (FTBVG7MNYD)"
app="dist/EyesOff.app"

tree -L 2 dist/EyesOff.app/Contents/Frameworks | head

# Step 1: Code sign the app with entitlements
echo "🔐 Step 1: Code signing application..."
codesign --deep --force --options runtime --entitlements EyesOff.entitlements --sign "Developer ID Application: Yusuf Mohammad (FTBVG7MNYD)" "dist/EyesOff.app"
check_status "Code signing"

# Step 2: Create ZIP archive for notarization
echo "📚 Step 2: Creating ZIP archive for notarization..."
ditto -c -k --keepParent "dist/EyesOff.app" "EyesOff.zip"
check_status "ZIP archive creation"

# Step 3: Submit for notarization
echo "☁️ Step 3: Submitting for notarization (this may take a while)..."
xcrun notarytool submit EyesOff.zip --keychain-profile EyesOffProfile --wait
check_status "Notarization submission"

# Step 4: Staple the ticket to the app
echo "🏷️ Step 4: Stapling notarization ticket to app..."
xcrun stapler staple "dist/EyesOff.app"
check_status "Stapling ticket to app"

# Step 5: Create temporary directory for DMG contents
echo "📁 Step 5: Creating temporary directory for DMG contents..."
mkdir -p /tmp/dmg-contents
check_status "Creating temporary directory"

# Step 6: Copy notarized app to temporary directory
echo "📋 Step 6: Copying notarized app to temporary directory..."
cp -R "dist/EyesOff.app" /tmp/dmg-contents/
check_status "Copying app to temporary directory"

# Step 6b: Re-staple the copied app
echo "🏷️  Step 6b: Restapling ticket inside DMG contents..."
xcrun stapler staple /tmp/dmg-contents/EyesOff.app
check_status "Restapling ticket in DMG payload"

echo "🔐 Step 6c: Re-signing the app in temporary directory..."
codesign --deep --force --options runtime --entitlements EyesOff.entitlements --sign "Developer ID Application: Yusuf Mohammad (FTBVG7MNYD)" "/tmp/dmg-contents/EyesOff.app"
check_status "Re-signing app in DMG contents"

# Step 7: Create the DMG
echo "💿 Step 7: Creating DMG..."
create-dmg \
  --volname "EyesOff" \
  --volicon "/Users/moose/Documents/PyCharm_Projects/EyesOff3/MyIcon.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "EyesOff.app" 200 190 \
  --app-drop-link 600 185 \
  --no-internet-enable \
  "./EyesOff.dmg" \
  "/tmp/dmg-contents/"
check_status "DMG creation"

# Step 8: Sign the DMG
echo "🔏 Step 8: Signing the DMG..."
codesign --sign "Developer ID Application: Yusuf Mohammad (FTBVG7MNYD)" --options runtime ./EyesOff.dmg
check_status "DMG signing"

# Step 9: Notarize the DMG
echo "☁️ Step 9: Notarizing the DMG (this may take a while)..."
xcrun notarytool submit ./EyesOff.dmg --keychain-profile EyesOffProfile --wait
check_status "DMG notarization"

# Step 10: Staple the notarization ticket to the DMG
echo "🏷️ Step 10: Stapling notarization ticket to DMG..."
xcrun stapler staple ./EyesOff.dmg
check_status "Stapling ticket to DMG"

# Create Sparkle ZIP
VERSION=$(defaults read "$PWD/dist/EyesOff.app/Contents/Info.plist" CFBundleShortVersionString)
cd dist && ditto -c -k --sequesterRsrc --keepParent EyesOff.app "../EyesOff-$VERSION.zip" && cd ..
./utils/generate_release_checksums.py "EyesOff-$VERSION.zip"
echo "✅ Created EyesOff-$VERSION.zip for updates"

# Clean up temporary files
echo "🧹 Cleaning up temporary files..."
rm -rf /tmp/dmg-contents
rm -f EyesOff.zip

echo "==================================================="
echo "✨ Build and notarization complete! ✨"
echo "DMG file available at: ./EyesOff.dmg"
echo "==================================================="

echo "==================================================="
echo "Creating Checksum"
./utils/generate_release_checksums.py ./EyesOff.dmg
echo "==================================================="
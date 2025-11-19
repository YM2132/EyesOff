# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.building.build_main import Tree

# Define the data files to include
added_files = [
	#('LaunchPad', 'MacOS'),
	#('frameworks/Sparkle.framework', 'Frameworks/Sparkle.framework'),
    ('models/face_detection_yunet_2023mar.onnx', 'models'),
	('models/best_classification_model_pretrain_finetune_VCD_and_customv2_b.onnx', 'models'),
    ('gui/resources/styles/default.qss', 'gui/resources/styles'),
]

a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,  # Add your data files here
    hiddenimports=['objc', 'Foundation', 'AppKit', 'PyObjC'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EyesOffPython',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity='Developer ID Application: Yusuf Mohammad (FTBVG7MNYD)',
    entitlements_file='EyesOff.entitlements',
    icon=['MyIcon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EyesOff',
)
app = BUNDLE(
    coll,
    name='EyesOff.app',
    icon='MyIcon.icns',
    bundle_identifier='app.eyesoff',
    entitlements_file='EyesOff.entitlements',
    codesign_identity='Developer ID Application: Yusuf Mohammad (FTBVG7MNYD)',
    info_plist={
        'CFBundleName': 'EyesOff',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleIdentifier': 'app.eyesoff',
        'CFBundleIconFile': 'MyIcon',
        'CFBundleExecutable': 'LaunchPad',
        'NSHumanReadableCopyright': 'Copyright © 2025 Yusuf Mohammad',
        'NSCameraUsageDescription': 'This app needs access to the camera for face detection',
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13',
        'NSUserNotificationAlertStyle': 'alert',
        'NSNotificationsUsageDescription': 'We need to send you privacy alerts when someone is looking at your screen.',

        # Sparkle Update Configuration
        'SUFeedURL': 'https://www.eyesoff.app/appcast.xml',
        'SUPublicEDKey': '5S/9ARAy5pYEX4IoN3R4Mm9iJ2F8Yk6G2BEDTQ8IHik=',
        'SUScheduledCheckInterval': 86400,  # Check daily (in seconds)
        'SUAutomaticallyUpdate': False,  # Prompt user before updating
        'SUEnableSystemProfiling': False,  # Don't send system info
    },
)

# Post-processing: CRITICAL FOR SPARKLE!
import shutil
import sys
import os

if sys.platform == 'darwin':
    print("Post-processing: Adding Sparkle framework and LaunchPad...")

    # FIRST: Clean up any wrong nested structure from previous builds
    wrong_nested = 'dist/EyesOff.app/Contents/Frameworks/Frameworks'
    if os.path.exists(wrong_nested):
        print(f"Cleaning up incorrect nested Frameworks directory...")
        shutil.rmtree(wrong_nested)

    # Ensure the Frameworks directory exists
    frameworks_dir = 'dist/EyesOff.app/Contents/Frameworks'

    # Copy Sparkle.framework to the CORRECT location
    src_sparkle = 'frameworks/Sparkle.framework'
    dst_sparkle = os.path.join(frameworks_dir, 'Sparkle.framework')

    if os.path.exists(src_sparkle):
        # Remove existing if present
        if os.path.exists(dst_sparkle):
            shutil.rmtree(dst_sparkle)

        # Copy with symlinks preserved (IMPORTANT for frameworks!)
        shutil.copytree(src_sparkle, dst_sparkle, symlinks=True)
        print(f"✓ Copied Sparkle.framework to {dst_sparkle}")
    else:
        print(f"⚠️  ERROR: Sparkle.framework not found at {src_sparkle}")
        sys.exit(1)

    # Copy LaunchPad
    src_launchpad = 'LaunchPad'
    dst_launchpad = 'dist/EyesOff.app/Contents/MacOS/LaunchPad'
    if os.path.exists(src_launchpad):
        shutil.copy2(src_launchpad, dst_launchpad)
        os.chmod(dst_launchpad, 0o755)
        print(f"✓ Copied LaunchPad")
    else:
        print(f"⚠️  Warning: {src_launchpad} not found - build it first!")

    print("Post-processing complete!")
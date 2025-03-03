# Distribution Guide for EyesOff

This guide explains how to package and distribute the EyesOff application for different platforms.

## Prerequisites

- Python 3.8+
- PyInstaller (`pip install pyinstaller`)
- Platform-specific build tools (optional)

## Basic Distribution with PyInstaller

### 1. Install PyInstaller

```bash
pip install pyinstaller
```

### 2. Create a Basic Executable

```bash
# Windows
pyinstaller --name EyesOff --onefile --windowed --icon=resources/icons/eyesoff.ico gui_main.py

# macOS
pyinstaller --name EyesOff --onefile --windowed --icon=resources/icons/eyesoff.icns gui_main.py

# Linux
pyinstaller --name EyesOff --onefile --windowed gui_main.py
```

### 3. Using a Spec File (Recommended)

Create a custom spec file for better control:

```python
# EyesOff.spec
a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('testing/mediapipe_testing/blaze_face_short_range.tflite', 'models'),
        ('gui/resources', 'resources')
    ],
    hiddenimports=['cv2', 'PyQt5', 'mediapipe'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EyesOff',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/eyesoff.ico'
)
```

Build using the spec file:

```bash
pyinstaller EyesOff.spec
```

## Platform-Specific Distribution

### Windows Installer

1. Install NSIS (Nullsoft Scriptable Install System)
2. Create `installer.nsi`:

```nsi
!include "MUI2.nsh"

Name "EyesOff Privacy Monitor"
OutFile "EyesOffSetup.exe"
InstallDir "$PROGRAMFILES\EyesOff"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File "dist\EyesOff.exe"
  File /r "dist\models\"
  File /r "dist\resources\"
  
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  CreateDirectory "$SMPROGRAMS\EyesOff"
  CreateShortcut "$SMPROGRAMS\EyesOff\EyesOff.lnk" "$INSTDIR\EyesOff.exe"
  CreateShortcut "$SMPROGRAMS\EyesOff\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\EyesOff.lnk" "$INSTDIR\EyesOff.exe"
  
  # Auto-start option (optional)
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "EyesOff" "$INSTDIR\EyesOff.exe"
  
  # Add uninstall information
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EyesOff" "DisplayName" "EyesOff Privacy Monitor"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EyesOff" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\EyesOff.exe"
  RMDir /r "$INSTDIR\models"
  RMDir /r "$INSTDIR\resources"
  Delete "$INSTDIR\Uninstall.exe"
  
  Delete "$SMPROGRAMS\EyesOff\EyesOff.lnk"
  Delete "$SMPROGRAMS\EyesOff\Uninstall.lnk"
  Delete "$DESKTOP\EyesOff.lnk"
  RMDir "$SMPROGRAMS\EyesOff"
  RMDir "$INSTDIR"
  
  # Remove auto-start entry
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "EyesOff"
  
  # Remove uninstall information
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EyesOff"
SectionEnd
```

3. Compile the installer:

```
makensis installer.nsi
```

### macOS DMG Creation

1. Create a macOS app bundle with PyInstaller:

```bash
pyinstaller --windowed --name "EyesOff" --icon=resources/icons/eyesoff.icns gui_main.py
```

2. Install `dmgbuild`:

```bash
pip install dmgbuild
```

3. Create a settings file `dmg_settings.py`:

```python
application = 'dist/EyesOff.app'
appname = 'EyesOff'
format = 'UDBZ'
size = '1g'
files = [application]
symlinks = {'Applications': '/Applications'}
badge_icon = 'resources/icons/eyesoff.icns'
background = 'resources/icons/dmg_background.png'
icon_locations = {
    appname: (140, 120),
    'Applications': (500, 120)
}
```

4. Build the DMG:

```bash
dmgbuild -s dmg_settings.py "EyesOff Privacy Monitor" EyesOff.dmg
```

### Linux Package (Debian/Ubuntu)

1. Create a basic directory structure:

```bash
mkdir -p build/deb/eyesoff/DEBIAN
mkdir -p build/deb/eyesoff/usr/bin
mkdir -p build/deb/eyesoff/usr/share/applications
mkdir -p build/deb/eyesoff/usr/share/icons/hicolor/256x256/apps
```

2. Create a control file at `build/deb/eyesoff/DEBIAN/control`:

```
Package: eyesoff
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Your Name <your.email@example.com>
Description: Privacy Protection Monitor
 EyesOff monitors your webcam for unauthorized viewers
 and displays an alert when someone else is looking at your screen.
Depends: libgtk-3-0
```

3. Copy the executable:

```bash
cp dist/EyesOff build/deb/eyesoff/usr/bin/eyesoff
chmod +x build/deb/eyesoff/usr/bin/eyesoff
```

4. Create desktop entry file at `build/deb/eyesoff/usr/share/applications/eyesoff.desktop`:

```
[Desktop Entry]
Type=Application
Name=EyesOff
GenericName=Privacy Monitor
Comment=Protect your privacy from unauthorized viewers
Exec=eyesoff
Icon=eyesoff
Terminal=false
Categories=Utility;Security;
```

5. Copy the icon:

```bash
cp resources/icons/eyesoff.png build/deb/eyesoff/usr/share/icons/hicolor/256x256/apps/eyesoff.png
```

6. Build the package:

```bash
dpkg-deb --build build/deb/eyesoff
```

## Additional Considerations

### Code Signing

For production distribution, code signing is recommended:

- **Windows**: Purchase a code signing certificate from a Certificate Authority
- **macOS**: Enroll in the Apple Developer Program for code signing
- **Linux**: Consider using distribution-specific signing methods

### Auto-Update Mechanism

Implement an update checker in your application:

```python
import requests
import packaging.version

def check_for_updates():
    try:
        response = requests.get('https://yourserver.com/eyesoff/version.json')
        latest_version = packaging.version.parse(response.json()['version'])
        current_version = packaging.version.parse("1.0.0")  # Your app's current version
        
        if latest_version > current_version:
            return {
                'available': True,
                'version': str(latest_version),
                'download_url': response.json()['download_url']
            }
    except Exception as e:
        print(f"Update check failed: {e}")
    
    return {'available': False}
```

### Distribution Channels

Consider these distribution channels:

- GitHub Releases
- Dedicated website with download links
- Package managers (pip, apt, brew, etc.)
- App stores (Microsoft Store, Mac App Store)

## Troubleshooting

- **Missing libraries**: Include any required DLLs or shared libraries with PyInstaller's `--add-binary` option
- **MediaPipe models**: Ensure model files are included in the correct location
- **Path issues**: Use absolute paths in your spec file for reliable builds

## Resources

- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)
- [NSIS Documentation](https://nsis.sourceforge.io/Docs/)
- [DMGBuild Documentation](https://dmgbuild.readthedocs.io/)
- [Debian Packaging Tutorial](https://www.debian.org/doc/manuals/packaging-tutorial/packaging-tutorial.en.pdf)
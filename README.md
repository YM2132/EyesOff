# EyesOff Privacy Monitor

EyesOff is a privacy protection application that monitors your webcam for unauthorized viewers and displays an alert when someone else is looking at your screen.

![EyesOff Screenshot](docs/screenshot.png)

## Features

- **Privacy Protection**: Alerts when unauthorized viewers are detected looking at your screen
- **Real-time Face Detection**: Uses MediaPipe for efficient face detection with support for additional models
- **Customizable Alerts**: Configure alert appearance, position, and behavior
- **System Integration**: System tray support and startup options
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Quick Start

### Installation

#### Option 1: Run from source code

1. Clone this repository:
   ```
   git clone https://github.com/username/eyesoff.git
   cd eyesoff
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python gui_main.py
   ```

### Using EyesOff

1. **Start Monitoring**: The application automatically starts monitoring when launched
2. **Control Panel**: Configure detection settings, alert appearance, and application preferences
3. **Stop/Start**: Use the Start/Stop button at the bottom left to pause monitoring
4. **System Tray**: Minimize to system tray to run in the background
5. **Alerts**: When multiple faces are detected, an alert appears until the privacy threat is gone

## Architecture

The application consists of two key components:

### Core Components

- **Webcam Management**: Captures video frames efficiently
- **Face Detection**: Multiple detector options with configurable thresholds
- **Alert System**: Shows visual warnings when privacy threats are detected 
- **Configuration System**: Stores user preferences and settings

### GUI Components

- **Main Window**: Application control center with menu and status bar
- **Webcam View**: Real-time display with detection visualization
- **Settings Panel**: Configurable options organized in tabs
- **Alert Dialog**: Customizable alerts with animations and sound

## Directory Structure

```
eyesoff/
├── core/               # Core functionality
│   ├── webcam.py       # Webcam management with PyQt signals
│   ├── detector.py     # Face detector wrapper with PyQt signals
│   └── manager.py      # Detection manager running in a separate thread
├── gui/                # GUI components
│   ├── main_window.py  # Main application window
│   ├── webcam_view.py  # Webcam display widget
│   ├── settings.py     # Settings panel implementation
│   ├── alert.py        # Alert dialog implementation
│   └── resources/      # Resources for the GUI
├── utils/              # Utility modules
├── gui_main.py         # GUI application entry point
└── main.py             # Command-line application entry point
```

## Command Line Usage

For headless operation, a command-line interface is also available:

```bash
python main.py [options]
```

Options:
- `--detector`: Choose face detector type (currently only mediapipe is fully implemented)
- `--model`: Path to detector model file
- `--confidence`: Detection confidence threshold (0.0-1.0)
- `--face-threshold`: Number of faces that triggers the alert
- `--camera`: Camera device ID
- `--width`: Frame width
- `--height`: Frame height
- `--no-animations`: Disable alert animations
- `--alert-position`: Position of the alert (center, top, bottom)
- `--debounce`: Debounce time for alerts (seconds)
- `--no-display`: Hide the detection visualization window

## Extending EyesOff

### Adding a New Detector

1. Create a new detector class implementing the detector interface
2. Add it to the available models in `core/detector.py`
3. Update the model type combo box in `gui/settings.py`

### Customizing Alerts

The alert system supports various customization options:
- Alert color and opacity
- Alert size and position
- Animation enabling/disabling
- Alert duration and dismissal options
- Sound alerts

## Building for Distribution

Use PyInstaller to create standalone executables:

```bash
# Install PyInstaller
pip install pyinstaller

# Build standalone executable
pyinstaller --name EyesOff --onefile --windowed --icon=path/to/icon.ico gui_main.py
```

For detailed distribution instructions, see [DISTRIBUTION.md](docs/DISTRIBUTION.md).

## Dependencies

- Python 3.8+
- OpenCV
- MediaPipe
- NumPy
- PyQt5

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
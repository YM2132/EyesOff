# EyesOff Privacy Monitor

EyesOff is a privacy protection application that uses your webcam to monitor for unauthorized viewers, notifying you when someone else looks at your screen.

![EyesOff Screenshot](https://github.com/user-attachments/assets/7e45274e-b5c1-44a4-9908-89d10b0100a0)


## Features

- **Privacy Protection**: Alerts when unauthorized viewers are detected looking at your screen
- **Real-time Face Detection**: Uses YuNet for efficient <b>local</b> face detection with support for additional models

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

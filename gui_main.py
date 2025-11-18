#!/usr/bin/env python3
import argparse
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QDialog

from gui.main_window import MainWindow


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="EyesOff Privacy Monitor GUI")
    
    parser.add_argument("--minimized", action="store_true",
                        help="Start minimized to system tray")
    parser.add_argument("--config", type=str,
                        help="Path to custom configuration file")
    parser.add_argument("--reset", action="store_true",
                        help="Reset all settings to defaults")
    
    return parser.parse_args()


def main():
    """Main entry point for the GUI application."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Create the Qt Application
    app = QApplication(sys.argv)

    # Set app icon
    app_icon = QIcon('gui/resources/icons/eyesoff_refined_logo.png')
    app.setWindowIcon((app_icon))

    # Set application info
    app.setApplicationName("EyesOff")
    app.setApplicationDisplayName("EyesOff Privacy Monitor")
    app.setOrganizationName("EyesOffApp")
    app.setOrganizationDomain("eyesoff.com")
    
    # Disable the ? button in dialogs on Windows
    app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
    
    # Create the main window
    window = MainWindow()
    
    # Handle startup options
    if args.reset:
        # Reset settings to defaults
        window._reset_settings()
    
    if args.minimized:
        # Start minimized to tray
        pass
    else:
        # Show the window
        window.show()
    
    # Start the application event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
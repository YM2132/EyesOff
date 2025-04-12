import json
import os
import sys
import subprocess
import tempfile
import requests

from PyQt5.QtCore import QObject, QThread, QEventLoop, QUrl, pyqtSignal
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from utils.config import ConfigManager


class UpdateManager(QObject):
    """Minimal GitHub update checker that only compares versions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.current_version = self.config_manager.get("app_version", "1.0.0")

        # GitHub repository information
        self.repo_owner = "YM2132"
        self.repo_name = "Eyes_Off"

        # Create the update thread
        self.thread = UpdateCheckerThread(self.repo_owner, self.repo_name, self.current_version)
        # self.thread.finished.connect(self.thread.deleteLater)

    def start(self):
        """Start the check for updates."""
        self.thread.start()

    def close_thread(self):
        """Properly close the update checker thread."""
        if self.thread and self.thread.isRunning():
            print('CLOSING DOWNLOAD THREAD')
            self.thread.requestInterruption()  # Signal the thread to stop
            self.thread.quit()  # End the event loop
            self.thread.wait()  # Wait for the thread to finish
            # Now it's safe to delete later
            self.thread.deleteLater()


class UpdateCheckerThread(QThread):
    """Thread that only checks if an update is available."""

    # Signal which is emitted if an update is available. Used to show the update view popup for user
    update_available = pyqtSignal(str)
    # Signal to trigger download, is emitted when the user clicks yes on update view dialogue
    start_download = pyqtSignal()
    # Download progress signal
    download_progress = pyqtSignal(int)  # Emits progress percentage
    download_completed = pyqtSignal(str)

    def __init__(self, repo_owner, repo_name, current_version):
        super().__init__()
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

        # Connect the start_download signal to the download method
        self.start_download.connect(self.download_update_dmg)

    def run(self):
        """Check for updates in background."""
        try:
            print(f"Checking for updates from GitHub ({self.repo_owner}/{self.repo_name})")
            print(f"Current version: {self.current_version}")
            self._check_for_update()
        except Exception as e:
            print(f"Update check error: {e}")

    def _check_for_update(self):
        """Check if an update is available on GitHub."""
        try:
            # Create network manager
            network_manager = QNetworkAccessManager()

            # Make the request to GitHub API
            request = QNetworkRequest(QUrl(self.github_api_url))
            request.setRawHeader(b"Accept", b"application/vnd.github.v3+json")
            request.setRawHeader(b"User-Agent", b"EyesOff-App")

            # Send the request
            reply = network_manager.get(request)

            # Wait for the request to finish
            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            loop.exec_()

            # Check if the request was successful
            if reply.error() != QNetworkReply.NoError:
                print(f"GitHub API error: {reply.errorString()}")
                return

            # Parse the JSON response
            data = reply.readAll().data().decode('utf-8')
            release_info = json.loads(data)

            # Extract version from tag name
            name = release_info.get('name', '')
            if not name:
                print("No version name found in release")
                return

            # Remove 'v' prefix if present
            latest_version = name[1:] if name.startswith('v') else name
            print(f"Latest version from GitHub: {latest_version}")

            # Compare versions
            if self._is_newer_version(latest_version, self.current_version):
                print(f"Update available: {latest_version}")
                self.update_available.emit(latest_version)
            else:
                print("No update available")

        except Exception as e:
            print(f"Error checking for update: {e}")

    def _is_newer_version(self, latest, current):
        """Compare version strings to determine if an update is available."""
        try:
            # Convert version strings to lists of integers
            latest_parts = [int(part) for part in latest.split('.')]
            current_parts = [int(part) for part in current.split('.')]

            # Compare each part of the version
            for i in range(max(len(latest_parts), len(current_parts))):
                latest_part = latest_parts[i] if i < len(latest_parts) else 0
                current_part = current_parts[i] if i < len(current_parts) else 0

                if latest_part > current_part:
                    return True
                elif latest_part < current_part:
                    return False

            return False  # Versions are equal
        except Exception as e:
            print(f"Error comparing versions: {e}")
            return False

    def download_update_dmg(self):
        print('DOWNLOADING')
        try:
            import requests
            import tempfile
            import os

            # 1. Get the latest release info
            response = requests.get(self.github_api_url,
                                    headers={"Accept": "application/vnd.github.v3+json",
                                             "User-Agent": "EyesOff-App"})
            response.raise_for_status()  # Raise exception if request failed
            release_info = response.json()

            # 2. Find the DMG asset in the release
            dmg_asset = None
            for asset in release_info.get('assets', []):
                if asset.get('name', '').endswith('.dmg'):
                    dmg_asset = asset
                    break

            if not dmg_asset:
                raise Exception("No DMG file found in the release assets")

            # Get the download URL
            download_url = dmg_asset.get('browser_download_url')
            if not download_url:
                raise Exception("No download URL found for the DMG asset")

            print(f"Found DMG download URL: {download_url}")

            # 3. Download the file with progress tracking
            print("Starting download...")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            # Get total file size if available
            total_size = int(response.headers.get('content-length', 0))

            # 4. Save to a temporary file
            filename = os.path.basename(download_url)
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)

            # Download with progress tracking
            downloaded = 0
            last_progress = 0

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Update progress (emit signal only when it changes by at least 1%)
                        if total_size > 0:
                            current_progress = int(100 * downloaded / total_size)
                            if current_progress > last_progress:
                                self.download_progress.emit(current_progress)
                                last_progress = current_progress
                                print(f"Download progress: {current_progress}%")

            print(f"Download completed successfully. File saved to: {file_path}")

            # 5. Open the DMG file
            if os.path.exists(file_path):
                if sys.platform == "darwin":  # macOS
                    # Instead of directly opening the DMG, just emit completion signal
                    # The UI will handle showing instructions and opening the file when ready
                    self.download_completed.emit(file_path)
                    print("Download completed. Ready for installation.")
                else:
                    print(f"Automatic installation not supported on {sys.platform}")
                    self.download_completed.emit(file_path)  # Still emit signal for UI update

            return file_path

        except Exception as e:
            print(f"Download error: {e}")
            return None
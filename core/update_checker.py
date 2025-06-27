import json
import os
import sys
import subprocess
import tempfile
import requests
import hashlib
import time

from PyQt5.QtCore import QObject, QThread, QEventLoop, QUrl, pyqtSignal, QCoreApplication
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from utils.config import ConfigManager
from utils.platform import get_platform_manager


class UpdateManager(QObject):
    """Minimal GitHub update checker that only compares versions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.platform_manager = get_platform_manager()
        self.config_manager = ConfigManager()
        #self.current_version = self.config_manager.get("app_version", "1.0.0")
        self.current_version = '1.0.0'

        # GitHub repository information
        self.repo_owner = "YM2132"
        self.repo_name = "EyesOff"

        # Create the update thread
        self.thread = UpdateCheckerThread(self.repo_owner, self.repo_name, self.current_version,
                                          self.config_manager)
        # self.thread.finished.connect(self.thread.deleteLater)

    def start(self):
        """Start the check for updates."""
        self.thread.start()

    def _shutdown(self):
        """Properly close the update checker thread."""
        if self.thread and self.thread.isRunning():
            print('CLOSING DOWNLOAD THREAD')
            self.thread.requestInterruption()  # Signal the thread to stop
            self.thread.quit()  # End the event loop
            self.thread.wait()  # Wait for the thread to finish
            # Now it's safe to delete later
            self.thread.deleteLater()

    @staticmethod
    def generate_checksum_file(file_path, output_dir=None):
        """
        Generate a SHA-256 checksum file for a given file.
        Used during the release process to create checksum files.

        Args:
            file_path: Path to the file to generate checksum for
            output_dir: Directory to save the checksum file (defaults to same dir as file)

        Returns:
            str: Path to the generated checksum file
        """
        try:
            # Calculate SHA-256 checksum
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            checksum = sha256_hash.hexdigest()

            # Determine output path
            if output_dir is None:
                output_dir = os.path.dirname(file_path)

            # Create checksum filename
            #base_name = os.path.splitext(os.path.basename(file_path))[0]
            #checksum_filename = f"{base_name}.checksum"
            checksum_filename = f"EyesOff.checksum"
            checksum_path = os.path.join(output_dir, checksum_filename)

            # Write checksum to file
            with open(checksum_path, 'w') as f:
                f.write(checksum)

            print(f"Generated checksum file: {checksum_path}")
            print(f"SHA-256: {checksum}")

            return checksum_path

        except Exception as e:
            print(f"Error generating checksum: {e}")
            return None


class UpdateCheckerThread(QThread):
    """Thread that only checks if an update is available."""

    # Signal which is emitted if an update is available. Used to show the update view popup for user
    update_available = pyqtSignal(str)
    # Signal to trigger download, is emitted when the user clicks yes on update view dialogue
    start_download = pyqtSignal()
    # Download progress signal
    download_progress = pyqtSignal(int)  # Emits progress percentage
    download_completed = pyqtSignal(str)

    def __init__(self, repo_owner, repo_name, current_version, config_manager):
        super().__init__()
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        #self.github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/tags/v1.1.0"  # To test pre-release change v{_._._} to match pre-release tag
        self.config_manager = config_manager
        self.platform_manager = get_platform_manager()
        self.latest_version = None

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
        """Check GitHub for the latest release."""
        try:
            # Create a synchronous request
            network_manager = QNetworkAccessManager()

            # Create event loop for synchronous operation
            loop = QEventLoop()

            # Track if we got a response
            got_response = False
            response_data = None

            def handle_response(reply):
                nonlocal got_response, response_data
                got_response = True

                if reply.error() == QNetworkReply.NetworkError.NoError:
                    response_data = reply.readAll().data()
                else:
                    print(f"Network error: {reply.errorString()}")

                reply.deleteLater()
                loop.quit()

            # Connect signal
            network_manager.finished.connect(handle_response)

            # Create request
            request = QNetworkRequest(QUrl(self.github_api_url))
            request.setRawHeader(b"Accept", b"application/vnd.github.v3+json")
            request.setRawHeader(b"User-Agent", b"EyesOff-App")

            # Make request
            network_manager.get(request)

            # Wait for response (with timeout)
            loop.exec()

            if got_response and response_data:
                # Parse the JSON response
                release_info = json.loads(response_data.decode('utf-8'))

                # Extract version from tag name (remove 'v' prefix if present)
                tag_name = release_info.get('tag_name', '')
                latest_version = tag_name.lstrip('v')

                if latest_version and self._is_newer_version(latest_version):
                    self.latest_version = latest_version
                    self.update_available.emit(latest_version)
                    print(f"New version available: {latest_version}")
                else:
                    print(f"No update available. Latest: {latest_version}")
            else:
                print("Failed to get update information")

        except Exception as e:
            print(f"Update check failed: {e}")

    def _is_newer_version(self, latest_version):
        """Compare version strings."""
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            latest_parts = [int(x) for x in latest_version.split('.')]

            # Pad with zeros if needed
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))

            return latest_parts > current_parts
        except:
            return False

    def download_update_dmg(self):
        """Simplified download that opens DMG automatically."""
        print('DOWNLOADING')
        try:
            import requests
            import tempfile
            import os
            import subprocess

            # Get release info
            response = requests.get(self.github_api_url,
                                    headers={"Accept": "application/vnd.github.v3+json",
                                             "User-Agent": "EyesOff-App"})
            response.raise_for_status()
            release_info = response.json()

            # Find DMG asset
            update_file_ext = self.platform_manager.update_manager.get_update_file_extension()
            update_asset = None
            for asset in release_info.get('assets', []):
                if asset.get('name', '').endswith(update_file_ext):
                    update_asset = asset
                    break

            if not update_asset:
                print(f"No {update_file_ext} file found")
                return

            download_url = update_asset.get('browser_download_url')
            if not download_url:
                print("No download URL found")
                return

            # Download with progress
            print(f"Downloading from: {download_url}")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            filename = os.path.basename(download_url)
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)

            downloaded = 0
            last_progress = 0

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.isInterruptionRequested():
                        print("Download cancelled")
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            current_progress = int(100 * downloaded / total_size)
                            if current_progress > last_progress:
                                self.download_progress.emit(current_progress)
                                last_progress = current_progress
                                QCoreApplication.processEvents()

            print(f"Download completed: {file_path}")

            # Silent verification
            if self._verify_download_silently(file_path, release_info):
                # Open DMG immediately
                subprocess.Popen(["open", file_path])

                self.config_manager.set("app_version", self.latest_version)
                self.download_completed.emit(file_path)
            else:
                print("Verification failed")
                if os.path.exists(file_path):
                    os.remove(file_path)

        except Exception as e:
            print(f"Download error: {e}")

    def _verify_download_silently(self, file_path, release_info):
        """Verify download without UI notifications."""
        try:
            # Try to get checksum
            expected_checksum = None
            for asset in release_info.get('assets', []):
                if asset.get('name') == "EyesOff.checksum":
                    checksum_url = asset.get('browser_download_url')
                    try:
                        checksum_response = requests.get(checksum_url)
                        checksum_response.raise_for_status()
                        expected_checksum = checksum_response.text.strip()
                    except:
                        pass

            # Calculate actual checksum
            with open(file_path, 'rb') as f:
                actual_checksum = hashlib.sha256(f.read()).hexdigest()

            if expected_checksum:
                return actual_checksum.lower() == expected_checksum.lower()
            else:
                print("Warning: No checksum available")
                return True

        except Exception as e:
            print(f"Verification error: {e}")
            return False
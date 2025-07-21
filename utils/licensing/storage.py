import json
import os
from datetime import datetime
from typing import Optional, Dict
from utils.platform import get_platform_manager


class LicenseStorage:
    """Handles storage of licensing and trial data."""
    
    def __init__(self):
        self.platform_manager = get_platform_manager()
        self.app_support_dir = self.platform_manager.file_system.get_app_support_directory()
        
        # File paths for trial and license data
        self.trial_file = os.path.join(self.app_support_dir, ".trial")
        self.license_file = os.path.join(self.app_support_dir, ".license")
    
    def get_trial_data(self) -> Optional[Dict]:
        """Load trial data from storage."""
        try:
            if os.path.exists(self.trial_file):
                with open(self.trial_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None
    
    def save_trial_data(self, data: Dict) -> bool:
        """Save trial data to storage."""
        try:
            with open(self.trial_file, 'w') as f:
                json.dump(data, f)
            return True
        except Exception:
            return False
    
    def start_trial(self) -> bool:
        """Initialize trial with current timestamp."""
        trial_data = {
            "start_date": datetime.now().isoformat(),
            "version": "1.0"
        }
        return self.save_trial_data(trial_data)
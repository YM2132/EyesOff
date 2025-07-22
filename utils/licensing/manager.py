from datetime import datetime, timedelta
from typing import Tuple
from utils.constants import TRIAL_DAYS, TEST_LICENSE_KEY
from .storage import LicenseStorage
from .crypto import LicenseVerifier


class LicensingManager:
	def __init__(self):
		self.storage = LicenseStorage()
		self.verifier = LicenseVerifier()
	
	def check_status(self) -> str:
		"""
		Check the current license status.
		
		Returns:
			str: "LICENSED", "TRIAL", or "EXPIRED"
		"""
		# First check if licensed
		license_data = self.storage.get_license_data()
		print(f"LICENSE: {license_data}")
		if license_data and license_data.get("key"):
			return "LICENSED"
		
		# Check trial status
		trial_data = self.storage.get_trial_data()
		if not trial_data:
			# First launch - start trial
			self.storage.start_trial()
			return "TRIAL"
		
		# Check if trial is still valid
		try:
			start_date = datetime.fromisoformat(trial_data["start_date"])
			current_date = datetime.now()
			days_elapsed = (current_date - start_date).days
			
			if days_elapsed < TRIAL_DAYS:
				return "TRIAL"
			else:
				return "EXPIRED"
		except Exception:
			# If we can't parse the date, assume expired
			return "EXPIRED"
	
	def activate_license(self, email: str, key: str) -> Tuple[bool, str]:
		"""
		Activate a license with email and key using ED25519 verification.
		
		Args:
			email: Customer email
			key: License key (base64 signature or TEST)
			
		Returns:
			Tuple[bool, str]: (success, message)
		"""
		# Basic input validation
		email = email.strip().lower()
		key = key.strip()
		
		if not email:
			return False, "Please enter your email address"
		
		if not key:
			return False, "Please enter your license key"
		
		# Verify the license using ED25519
		if self.verifier.verify_license(email, key):
			# Save license data
			if self.storage.save_license_data(email, key):
				return True, "License activated successfully!"
			else:
				return False, "Failed to save license data"
		else:
			return False, "Invalid license key"
	
	def get_trial_days_remaining(self) -> int:
		"""Get the number of trial days remaining."""
		trial_data = self.storage.get_trial_data()
		if not trial_data:
			return TRIAL_DAYS
		
		try:
			start_date = datetime.fromisoformat(trial_data["start_date"])
			current_date = datetime.now()
			days_elapsed = (current_date - start_date).days
			days_remaining = TRIAL_DAYS - days_elapsed
			return max(0, days_remaining)
		except Exception:
			return 0
	
	def is_licensed(self) -> bool:
		"""Check if the app is licensed."""
		return self.check_status() == "LICENSED"
	
	def check_license_status(self):
		"""Legacy method for compatibility."""
		return self.is_licensed()

import os
import sys

# Define project root once at the module level
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative_path):
	"""Get absolute path to resource, works for dev and for PyInstaller"""
	if getattr(sys, 'frozen', False):
		# Running in a bundle
		base_path = sys._MEIPASS
	else:
		# Just use the project root we defined once
		base_path = PROJECT_ROOT

	return os.path.join(base_path, relative_path)
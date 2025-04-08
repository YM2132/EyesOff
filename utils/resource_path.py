import os
import sys


def resource_path(relative_path):
	"""Get absolute path to resource, works for dev and for PyInstaller"""
	if getattr(sys, 'frozen', False):
		# Running in a bundle
		base_path = sys._MEIPASS
	else:
		# Running in normal Python environment
		base_path = os.path.dirname(os.path.abspath(__file__))

	return os.path.join(base_path, relative_path)
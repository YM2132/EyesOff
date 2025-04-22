import os
from Foundation import NSFileManager, NSSearchPathForDirectoriesInDomains, NSApplicationSupportDirectory, \
	NSUserDomainMask


def get_app_support_dir():
	# Get the application support directory path
	file_manager = NSFileManager.defaultManager()
	paths = NSSearchPathForDirectoriesInDomains(NSApplicationSupportDirectory, NSUserDomainMask, True)
	base_path = paths[0]
	app_support_dir = os.path.join(base_path, "app.eyesoff")  # Use your bundle ID

	# Create the directory if it doesn't exist
	if not os.path.exists(app_support_dir):
		os.makedirs(app_support_dir)

	return app_support_dir


# Then use this for your files
def get_config_path():
	return os.path.join(get_app_support_dir(), "config.json")


def get_snapshots_dir():
	snapshots_dir = os.path.join(get_app_support_dir(), "snapshots")
	if not os.path.exists(snapshots_dir):
		os.makedirs(snapshots_dir)
	return snapshots_dir
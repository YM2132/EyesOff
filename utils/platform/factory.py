"""Factory for creating platform-specific managers."""

import platform
from typing import TYPE_CHECKING

from .base import PlatformManager

if TYPE_CHECKING:
    # Import for type checking only
    from .macos import MacOSPlatformManager
    from .windows import WindowsPlatformManager


def get_platform_manager() -> PlatformManager:
    """
    Get the appropriate platform manager for the current OS.
    
    Returns:
        PlatformManager: Platform-specific manager instance
        
    Raises:
        NotImplementedError: If the platform is not supported
    """
    system = platform.system()
    
    if system == 'Darwin':
        from .macos import MacOSPlatformManager
        return MacOSPlatformManager()
    elif system == 'Windows':
        from .windows import WindowsPlatformManager
        return WindowsPlatformManager()
    else:
        raise NotImplementedError(f"Platform {system} is not supported")
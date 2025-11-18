"""
PumaGuard
"""

import importlib.metadata

try:
    import setuptools
except ModuleNotFoundError:
    import sys

    print("Unable to load setuptools")
    print(sys.path)
    raise

try:
    __version__ = importlib.metadata.version("pumaguard")
    __VERSION__ = __version__  # Keep for backward compatibility
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"
    __VERSION__ = __version__

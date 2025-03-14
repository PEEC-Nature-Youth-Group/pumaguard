"""
PumaGuard
"""

import importlib.metadata

try:
    import setuptools
except ModuleNotFoundError:
    import sys
    print('Unable to load setuptools')
    print(sys.path)
    raise

try:
    __VERSION__ = importlib.metadata.version('pumaguard')
except importlib.metadata.PackageNotFoundError:
    __VERSION__ = 'undefined'

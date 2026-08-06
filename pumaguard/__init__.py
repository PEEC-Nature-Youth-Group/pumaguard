"""
PumaGuard
"""

import importlib.metadata
import os

# Limit BLAS/OpenMP thread pools *before* any heavy native ML libraries
# (TensorFlow/Keras, PyTorch/Ultralytics) are imported anywhere in this
# package. Mixing multiple such libraries in one process, each spinning up
# its own multi-threaded BLAS/OpenMP thread pool, is a well-known source of
# native crashes (including SIGSEGV) on ARM/Raspberry Pi. These must be set
# here, at the very top of the package's __init__, because setting them
# later (e.g. inside main()) is too late: by then pumaguard.server has
# already imported pumaguard.utils, which imports keras/torch/ultralytics,
# and those libraries read these variables once, during their own
# initialization. Only set them if the user/operator hasn't already chosen
# a value.
for _thread_env_var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_thread_env_var, "1")
del _thread_env_var

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

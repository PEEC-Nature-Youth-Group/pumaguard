"""
Create an instance of a Model.
"""

from pumaguard.models import (
    __MODELS__,
)
from pumaguard.presets import (
    Preset,
)


def model_factory(presets: Preset):
    """
    Create an instance of a Model.
    """
    if presets.model_function_name not in __MODELS__:
        raise ValueError(f"unknown model {presets.model_function_name}")
    return __MODELS__[presets.model_function_name](
        presets
    )  # type: ignore[abstract]

"""
The models.
"""

from pumaguard.models import (
    light_1,
    light_2,
    light_3,
    light_4,
    mobilenetv3,
    xception,
)

__MODELS__ = {
    'xception': xception.XceptionModel,
    'light-model': light_1.LightModel1,
    'light-2-model': light_2.LightModel2,
    'light-3-model': light_3.LightModel3,
    'mobilenetv3': mobilenetv3.MobileNetV3Model,
    'conv2d-model': light_4.LightModel4,
}

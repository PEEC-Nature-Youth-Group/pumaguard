"""
The models.
"""

from pumaguard.models import (
    conv2d,
    light,
    light_2,
    light_3,
    mobilenetv3,
    pretrained,
)

__MODELS__ = {
    'pretrained': pretrained.PretrainedModel,
    'light-model': light.LightModel,
    'light-2-model': light_2.LightModel2,
    'light-3-model': light_3.LightModel3,
    'mobilenetv3': mobilenetv3.MobileNetV3Model,
    'conv2d-model': conv2d.Conv2DModel,
}

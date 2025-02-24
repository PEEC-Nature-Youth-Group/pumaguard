"""
Test raw xception labels.
"""

import os

import numpy as np
from keras.applications.xception import (  # pylint: disable=import-error
    Xception,
    decode_predictions,
    preprocess_input,
)
from tensorflow.keras.preprocessing import (  # pylint: disable=import-error,no-name-in-module
    image,
)

model = Xception(weights='imagenet')


def load_and_preprocess_image(img_path):
    """
    Load and preprocess image.
    """
    img = image.load_img(img_path, target_size=(299, 299))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    return img_array


def main():
    """
    Main function.
    """
    for img_path in ['lion/' + img for img
                     in os.listdir('data/stable/stable_test/lion')] + \
            ['no-lion/' + img for img
                in os.listdir('data/stable/stable_test/no-lion')]:
        img_array = load_and_preprocess_image(
            'data/stable/stable_test/' + img_path)
        predictions = model.predict(img_array)
        decoded_predictions = decode_predictions(predictions, top=5)[0]
        print(f'{img_path}:')
        for i, (imagenet_id, label, score) in enumerate(decoded_predictions):
            print(f'{i + 1}: {imagenet_id} {100 * score:6.2f}% {label}')


if __name__ == '__main__':
    main()

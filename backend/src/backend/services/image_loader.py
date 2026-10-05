"""Shared conversion of application image inputs to RGB NumPy arrays."""

from __future__ import annotations

from io import BytesIO
from os import PathLike
from typing import BinaryIO, TypeAlias

import face_recognition
import numpy as np
from numpy.typing import NDArray

RGBImage: TypeAlias = NDArray[np.uint8]
ImageInput: TypeAlias = str | PathLike[str] | bytes | bytearray | BinaryIO | RGBImage


class InvalidImageError(ValueError):
    """Raised when input cannot be decoded as a valid RGB image."""


def load_rgb_image(image: ImageInput) -> RGBImage:
    """Return an RGB image accepted by ``face_recognition``.

    NumPy input is assumed to already use RGB channel order. OpenCV camera frames
    use BGR and must be converted to RGB before calling this function.
    """

    if isinstance(image, np.ndarray):
        loaded = image
    else:
        source = BytesIO(image) if isinstance(image, (bytes, bytearray)) else image
        try:
            loaded = face_recognition.load_image_file(source, mode="RGB")
        except (OSError, TypeError, ValueError) as error:
            raise InvalidImageError("image could not be decoded") from error

    if loaded.dtype != np.uint8:
        raise InvalidImageError("image array must use uint8 values")
    if loaded.ndim != 3 or loaded.shape[2] != 3:
        raise InvalidImageError("image must have exactly three RGB channels")
    if loaded.shape[0] == 0 or loaded.shape[1] == 0:
        raise InvalidImageError("image cannot be empty")

    return np.ascontiguousarray(loaded)

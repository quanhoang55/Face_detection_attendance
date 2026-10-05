"""Generate a reusable face encoding for employee enrollment."""

from __future__ import annotations

from dataclasses import dataclass

import face_recognition
import numpy as np
from numpy.typing import NDArray

from backend.config import Settings
from backend.services.image_loader import ImageInput, load_rgb_image

FaceEncoding = NDArray[np.float64]
FaceLocation = tuple[int, int, int, int]


class FaceEncodingError(ValueError):
    """Base error for images that cannot be used for enrollment."""


class NoFaceFoundError(FaceEncodingError):
    """Raised when an enrollment image contains no detectable face."""


class MultipleFacesFoundError(FaceEncodingError):
    """Raised when an enrollment image contains more than one face."""


@dataclass(frozen=True, slots=True)
class EncodedFace:
    """A validated enrollment encoding and its source-image location."""

    encoding: FaceEncoding
    location: FaceLocation


class FaceEncoder:
    """Create exactly one 128-dimensional face encoding from an image."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def encode(self, image: ImageInput) -> EncodedFace:
        """Encode an enrollment image that contains exactly one face."""

        rgb_image = load_rgb_image(image)
        locations = face_recognition.face_locations(
            rgb_image,
            number_of_times_to_upsample=self._settings.number_of_times_to_upsample,
            model=self._settings.detection_model,
        )

        if not locations:
            raise NoFaceFoundError("enrollment image must contain one face; none found")
        if len(locations) > 1:
            raise MultipleFacesFoundError(
                f"enrollment image must contain one face; found {len(locations)}"
            )

        encodings = face_recognition.face_encodings(
            rgb_image,
            known_face_locations=locations,
            num_jitters=self._settings.number_of_jitters,
            model=self._settings.encoding_model,
        )
        if len(encodings) != 1:
            raise FaceEncodingError("the detected face could not be encoded")

        encoding = np.asarray(encodings[0], dtype=np.float64)
        if encoding.shape != (128,):
            raise FaceEncodingError(
                f"expected a 128-value face encoding; received shape {encoding.shape}"
            )

        return EncodedFace(encoding=encoding, location=locations[0])

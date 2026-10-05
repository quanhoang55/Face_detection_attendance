import unittest
from unittest.mock import patch

import numpy as np

from backend.config import Settings
from backend.services.face_encoder import (
    FaceEncoder,
    MultipleFacesFoundError,
    NoFaceFoundError,
)


class FaceEncoderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = np.zeros((100, 100, 3), dtype=np.uint8)
        self.encoder = FaceEncoder(Settings())

    @patch("backend.services.face_encoder.face_recognition.face_locations")
    def test_no_face_is_rejected(self, face_locations) -> None:
        face_locations.return_value = []

        with self.assertRaises(NoFaceFoundError):
            self.encoder.encode(self.image)

    @patch("backend.services.face_encoder.face_recognition.face_locations")
    def test_multiple_faces_are_rejected(self, face_locations) -> None:
        face_locations.return_value = [(1, 2, 3, 0), (4, 5, 6, 3)]

        with self.assertRaises(MultipleFacesFoundError):
            self.encoder.encode(self.image)

    @patch("backend.services.face_encoder.face_recognition.face_encodings")
    @patch("backend.services.face_encoder.face_recognition.face_locations")
    def test_one_face_produces_128_value_encoding(
        self, face_locations, face_encodings
    ) -> None:
        location = (10, 80, 90, 20)
        face_locations.return_value = [location]
        face_encodings.return_value = [np.arange(128, dtype=np.float64)]

        result = self.encoder.encode(self.image)

        self.assertEqual(result.location, location)
        self.assertEqual(result.encoding.shape, (128,))


if __name__ == "__main__":
    unittest.main()

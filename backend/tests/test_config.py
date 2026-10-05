import os
import unittest
from unittest.mock import patch

from backend.config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_valid(self) -> None:
        settings = Settings()

        self.assertEqual(settings.recognition_tolerance, 0.55)
        self.assertEqual(settings.detection_model, "hog")
        self.assertEqual(settings.recognition_frame_scale, 0.5)

    def test_settings_are_loaded_from_environment(self) -> None:
        environment = {
            "FACE_RECOGNITION_TOLERANCE": "0.48",
            "FACE_DETECTION_MODEL": "cnn",
            "FACE_ENCODING_MODEL": "large",
            "FACE_DETECTION_UPSAMPLE": "2",
            "FACE_ENCODING_JITTERS": "3",
            "FACE_RECOGNITION_FRAME_SCALE": "0.25",
        }

        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.recognition_tolerance, 0.48)
        self.assertEqual(settings.detection_model, "cnn")
        self.assertEqual(settings.encoding_model, "large")
        self.assertEqual(settings.number_of_times_to_upsample, 2)
        self.assertEqual(settings.number_of_jitters, 3)
        self.assertEqual(settings.recognition_frame_scale, 0.25)

    def test_invalid_tolerance_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "recognition_tolerance"):
            Settings(recognition_tolerance=1.1)


if __name__ == "__main__":
    unittest.main()

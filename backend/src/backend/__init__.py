"""Core face recognition package."""

from backend.config import Settings
from backend.services.face_encoder import FaceEncoder
from backend.services.face_recognizer import FaceRecognizer

__all__ = ["FaceEncoder", "FaceRecognizer", "Settings"]

"""Validation for image files received by API routes."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from backend.config import Settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


class UploadValidationError(ValueError):
    status_code = 422


class UnsupportedImageTypeError(UploadValidationError):
    status_code = 415


class ImageTooLargeError(UploadValidationError):
    status_code = 413


class UploadService:
    def __init__(self, settings: Settings) -> None:
        self._max_upload_bytes = settings.max_upload_bytes

    def read_image(
        self, file: BinaryIO, filename: str | None, content_type: str | None
    ) -> bytes:
        """Validate and read an uploaded JPG or PNG without unbounded allocation."""

        if not filename:
            raise UploadValidationError("an image filename is required")
        if Path(filename).suffix.casefold() not in ALLOWED_EXTENSIONS:
            raise UnsupportedImageTypeError("image must be a .jpg, .jpeg, or .png file")
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedImageTypeError("image content type must be JPEG or PNG")

        image_bytes = file.read(self._max_upload_bytes + 1)
        if len(image_bytes) > self._max_upload_bytes:
            raise ImageTooLargeError(
                f"image exceeds the {self._max_upload_bytes}-byte upload limit"
            )
        if not image_bytes:
            raise UploadValidationError("image cannot be empty")
        return image_bytes

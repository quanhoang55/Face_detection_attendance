"""Translate domain validation errors into HTTP responses."""

from fastapi import HTTPException

from backend.repositories.employee_csv import DuplicateEmployeeError
from backend.services.employee_service import InvalidEmployeeNameError
from backend.services.face_encoder import FaceEncodingError
from backend.services.image_loader import InvalidImageError
from backend.services.upload_service import UploadValidationError


def as_http_exception(error: ValueError) -> HTTPException:
    if isinstance(error, DuplicateEmployeeError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, UploadValidationError):
        return HTTPException(status_code=error.status_code, detail=str(error))
    if isinstance(
        error, (InvalidEmployeeNameError, FaceEncodingError, InvalidImageError)
    ):
        return HTTPException(status_code=422, detail=str(error))
    return HTTPException(status_code=500, detail="internal application error")

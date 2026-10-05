"""FastAPI application and service composition root."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.config import Settings
from backend.logging_config import configure_logging
from backend.repositories.attendance_csv import AttendanceCsvRepository
from backend.repositories.employee_csv import EmployeeCsvRepository
from backend.services.attendance_service import AttendanceService
from backend.services.employee_service import EmployeeService
from backend.services.face_encoder import FaceEncoder
from backend.services.face_recognizer import FaceRecognizer
from backend.services.recognition_service import RecognitionService
from backend.services.upload_service import UploadService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CoreServices:
    settings: Settings
    face_encoder: FaceEncoder
    face_recognizer: FaceRecognizer
    employee_repository: EmployeeCsvRepository
    attendance_repository: AttendanceCsvRepository
    upload_service: UploadService
    attendance_service: AttendanceService
    employee_service: EmployeeService
    recognition_service: RecognitionService


def create_core(settings: Settings | None = None) -> CoreServices:
    """Create repositories and application services."""

    resolved_settings = settings or Settings.from_env()
    timezone = ZoneInfo(resolved_settings.timezone)

    def clock() -> datetime:
        return datetime.now(timezone)

    face_encoder = FaceEncoder(resolved_settings)
    face_recognizer = FaceRecognizer(resolved_settings)
    employee_repository = EmployeeCsvRepository(
        resolved_settings.data_dir / "employees.csv"
    )
    attendance_repository = AttendanceCsvRepository(
        resolved_settings.data_dir / "attendance.csv"
    )
    attendance_service = AttendanceService(attendance_repository, clock)
    return CoreServices(
        settings=resolved_settings,
        face_encoder=face_encoder,
        face_recognizer=face_recognizer,
        employee_repository=employee_repository,
        attendance_repository=attendance_repository,
        upload_service=UploadService(resolved_settings),
        attendance_service=attendance_service,
        employee_service=EmployeeService(
            employee_repository,
            attendance_service,
            face_encoder,
            clock,
        ),
        recognition_service=RecognitionService(
            employee_repository,
            attendance_service,
            face_recognizer,
        ),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the HTTP application without adding undocumented endpoints."""

    from backend.api.employees import router as employee_router
    from backend.api.recognition import router as recognition_router

    resolved_settings = settings or Settings.from_env()
    configure_logging(resolved_settings.log_level)
    core = create_core(resolved_settings)
    application = FastAPI(title="Face Recognition Attendance API", version="0.1.0")
    application.state.core = core

    data_dir = core.settings.data_dir.resolve()
    employee_count = len(core.employee_repository.list_all())
    logger.info(
        "Backend started | data_dir=%s | employees_csv=%s | attendance_csv=%s | "
        "employees_loaded=%d | tolerance=%.3f | detection_model=%s",
        data_dir,
        data_dir / "employees.csv",
        data_dir / "attendance.csv",
        employee_count,
        core.settings.recognition_tolerance,
        core.settings.detection_model,
    )

    @application.middleware("http")
    async def log_http_request(request: Request, call_next) -> Response:
        started_at = perf_counter()
        logger.debug(
            "Request started | method=%s | path=%s",
            request.method,
            request.url.path,
        )
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled request error | method=%s | path=%s",
                request.method,
                request.url.path,
            )
            raise
        logger.info(
            "Request completed | method=%s | path=%s | status=%d | duration_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started_at) * 1000,
        )
        return response

    if core.settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(core.settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    application.include_router(employee_router)
    application.include_router(recognition_router)
    return application


app = create_app()


def main() -> None:
    """Run the development ASGI server."""

    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()

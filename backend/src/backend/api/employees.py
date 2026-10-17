"""Employee enrollment and listing routes."""

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from backend.api.dependencies import get_core
from backend.api.errors import as_http_exception, database_http_exception
from backend.main import CoreServices
from backend.models.schemas import EmployeeAttendance, EmployeeCreated

router = APIRouter(prefix="/api", tags=["employees"])
logger = logging.getLogger(__name__)


@router.post(
    "/employees",
    response_model=EmployeeCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    name: Annotated[str, Form()],
    image: Annotated[UploadFile, File()],
    core: Annotated[CoreServices, Depends(get_core)],
) -> EmployeeCreated:
    logger.info(
        "Enrollment requested | name=%r | filename=%r | content_type=%r",
        name,
        image.filename,
        image.content_type,
    )
    try:
        image_bytes = core.upload_service.read_image(
            image.file, image.filename, image.content_type
        )
        created = core.employee_service.enroll(
            name=name,
            image_filename=image.filename or "",
            image=image_bytes,
        )
        logger.info(
            "Enrollment completed | employee_id=%s | name=%r | image_bytes=%d",
            created.employee_id,
            created.name,
            len(image_bytes),
        )
        return created
    except ValueError as error:
        logger.warning(
            "Enrollment rejected | name=%r | filename=%r | error=%s",
            name,
            image.filename,
            error,
        )
        raise as_http_exception(error) from error
    except Exception as error:
        logger.exception("Employee enrollment storage failed | name=%r", name)
        raise database_http_exception(error) from error
    finally:
        image.file.close()


@router.get("/employees", response_model=list[EmployeeAttendance])
def list_employees(
    core: Annotated[CoreServices, Depends(get_core)],
) -> list[EmployeeAttendance]:
    try:
        employees = core.employee_service.list_with_attendance()
    except Exception as error:
        logger.exception("Employee list storage failed")
        raise database_http_exception(error) from error
    logger.info(
        "Employee list loaded | total=%d | arrived=%d",
        len(employees),
        sum(employee.is_arrive for employee in employees),
    )
    return employees


@router.get("/attendance", response_model=list[EmployeeAttendance])
def list_attendance(
    core: Annotated[CoreServices, Depends(get_core)],
    attendance_date: Annotated[date | None, Query(alias="date")] = None,
) -> list[EmployeeAttendance]:
    try:
        employees = core.employee_service.list_with_attendance(attendance_date)
    except Exception as error:
        logger.exception("Attendance list storage failed")
        raise database_http_exception(error) from error
    logger.info(
        "Attendance list loaded | requested_date=%s | total=%d | arrived=%d",
        attendance_date or "today",
        len(employees),
        sum(employee.is_arrive for employee in employees),
    )
    return employees

"""Employee enrollment and attendance-list application service."""

from __future__ import annotations

import logging
from datetime import date, datetime
from threading import Lock
from typing import Callable

from backend.models.domain import Employee
from backend.models.schemas import EmployeeAttendance, EmployeeCreated
from backend.repositories.employee_csv import EmployeeCsvRepository
from backend.services.attendance_service import AttendanceService
from backend.services.face_encoder import FaceEncoder

Clock = Callable[[], datetime]
logger = logging.getLogger(__name__)


class InvalidEmployeeNameError(ValueError):
    pass


class EmployeeService:
    def __init__(
        self,
        employee_repository: EmployeeCsvRepository,
        attendance_service: AttendanceService,
        face_encoder: FaceEncoder,
        clock: Clock,
    ) -> None:
        self._employees = employee_repository
        self._attendance = attendance_service
        self._face_encoder = face_encoder
        self._clock = clock
        self._enrollment_lock = Lock()

    def enroll(self, name: str, image_filename: str, image: bytes) -> EmployeeCreated:
        normalized_name = " ".join(name.split())
        if not normalized_name:
            raise InvalidEmployeeNameError("employee name cannot be empty")
        if len(normalized_name) > 120:
            raise InvalidEmployeeNameError("employee name cannot exceed 120 characters")

        logger.info(
            "Encoding enrollment face | name=%r | filename=%r | image_bytes=%d",
            normalized_name,
            image_filename,
            len(image),
        )
        encoded_face = self._face_encoder.encode(image)
        logger.info(
            "Enrollment face encoded | name=%r | face_location=%s",
            normalized_name,
            encoded_face.location,
        )
        with self._enrollment_lock:
            employee = Employee(
                employee_id=self._employees.next_id(),
                name=normalized_name,
                image_filename=image_filename,
                face_encoding=encoded_face.encoding,
                created_at=self._clock(),
            )
            self._employees.create(employee)
        logger.info(
            "Employee persisted | employee_id=%s | name=%r",
            employee.employee_id,
            employee.name,
        )

        return EmployeeCreated(
            employee_id=employee.employee_id,
            name=employee.name,
            image_filename=employee.image_filename,
        )

    def list_with_attendance(
        self, attendance_date: date | None = None
    ) -> list[EmployeeAttendance]:
        selected_date = self._attendance.date_or_today(attendance_date)
        attendance_by_employee = self._attendance.by_employee_for_date(selected_date)
        employees = self._employees.list_all()
        result = [
            EmployeeAttendance(
                employee_id=employee.employee_id,
                name=employee.name,
                is_arrive=employee.employee_id in attendance_by_employee,
                arrived_at=(
                    attendance_by_employee[employee.employee_id].arrived_at
                    if employee.employee_id in attendance_by_employee
                    else None
                ),
            )
            for employee in employees
        ]
        logger.debug(
            "Employee attendance view composed | date=%s | employees=%d | arrivals=%d",
            selected_date,
            len(result),
            len(attendance_by_employee),
        )
        return result

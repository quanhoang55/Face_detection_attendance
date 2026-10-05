"""Daily attendance application service."""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable

from backend.models.domain import Attendance
from backend.repositories.attendance_csv import AttendanceCsvRepository

Clock = Callable[[], datetime]


class AttendanceService:
    def __init__(
        self, attendance_repository: AttendanceCsvRepository, clock: Clock
    ) -> None:
        self._attendance = attendance_repository
        self._clock = clock

    def date_or_today(self, attendance_date: date | None) -> date:
        return attendance_date or self._clock().date()

    def by_employee_for_date(
        self, attendance_date: date
    ) -> dict[str, Attendance]:
        return {
            item.employee_id: item
            for item in self._attendance.list_for_date(attendance_date)
        }

    def mark_arrived(self, employee_id: str, distance: float) -> bool:
        return self._attendance.mark_arrived(
            employee_id=employee_id,
            arrived_at=self._clock(),
            distance=distance,
        )

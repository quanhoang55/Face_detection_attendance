"""CSV implementation of employee persistence."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from threading import RLock

import numpy as np

from backend.models.domain import Employee
from backend.repositories.csv_utils import atomic_write_rows, ensure_csv, read_rows

FIELDS = ("employee_id", "name", "image_filename", "face_encoding", "created_at")
logger = logging.getLogger(__name__)


class DuplicateEmployeeError(ValueError):
    """Raised when an employee name is already enrolled."""


class EmployeeCsvRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = RLock()
        with self._lock:
            ensure_csv(self._path, FIELDS)
        logger.info("Employee CSV ready | path=%s", self._path.resolve())

    def list_all(self) -> list[Employee]:
        with self._lock:
            employees = [self._deserialize(row) for row in read_rows(self._path)]
        logger.debug(
            "Employee CSV read | path=%s | rows=%d",
            self._path.resolve(),
            len(employees),
        )
        return employees

    def get_by_id(self, employee_id: str) -> Employee | None:
        return next(
            (employee for employee in self.list_all() if employee.employee_id == employee_id),
            None,
        )

    def name_exists(self, name: str) -> bool:
        normalized_name = name.strip().casefold()
        return any(
            employee.name.casefold() == normalized_name for employee in self.list_all()
        )

    def create(self, employee: Employee) -> Employee:
        with self._lock:
            employees = [self._deserialize(row) for row in read_rows(self._path)]
            if any(item.name.casefold() == employee.name.casefold() for item in employees):
                raise DuplicateEmployeeError(
                    f"an employee named {employee.name!r} is already enrolled"
                )
            if not employee.employee_id:
                highest = 0
                for item in employees:
                    prefix, separator, numeric_id = item.employee_id.partition("_")
                    if prefix == "emp" and separator and numeric_id.isdigit():
                        highest = max(highest, int(numeric_id))
                employee = replace(employee, employee_id=f"emp_{highest + 1:03d}")
            employees.append(employee)
            atomic_write_rows(
                self._path, FIELDS, (self._serialize(item) for item in employees)
            )
        logger.info(
            "Employee CSV written | path=%s | employee_id=%s | rows=%d",
            self._path.resolve(),
            employee.employee_id,
            len(employees),
        )
        return employee

    def next_id(self) -> str:
        with self._lock:
            highest = 0
            for row in read_rows(self._path):
                prefix, separator, numeric_id = row["employee_id"].partition("_")
                if prefix == "emp" and separator and numeric_id.isdigit():
                    highest = max(highest, int(numeric_id))
            return f"emp_{highest + 1:03d}"

    @staticmethod
    def _serialize(employee: Employee) -> dict[str, object]:
        return {
            "employee_id": employee.employee_id,
            "name": employee.name,
            "image_filename": employee.image_filename,
            "face_encoding": json.dumps(employee.face_encoding.tolist()),
            "created_at": employee.created_at.isoformat(),
        }

    @staticmethod
    def _deserialize(row: dict[str, str]) -> Employee:
        encoding = np.asarray(json.loads(row["face_encoding"]), dtype=np.float64)
        if encoding.shape != (128,):
            raise ValueError(
                f"stored encoding for {row['employee_id']!r} must have 128 values"
            )
        return Employee(
            employee_id=row["employee_id"],
            name=row["name"],
            image_filename=row["image_filename"],
            face_encoding=encoding,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

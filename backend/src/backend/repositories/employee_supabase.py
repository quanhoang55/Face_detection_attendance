"""Supabase Data API implementation of employee persistence."""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np

from backend.models.domain import Employee
from backend.repositories.employee_csv import DuplicateEmployeeError
from backend.repositories.supabase_rest import SupabaseRestClient, SupabaseRequestError

logger = logging.getLogger(__name__)


class EmployeeSupabaseRepository:
    def __init__(self, client: SupabaseRestClient) -> None:
        self._client = client

    def list_all(self) -> list[Employee]:
        rows = self._client.request(
            "GET", "employees", query={"select": "*", "order": "created_at.asc"}
        )
        return [self._deserialize(row) for row in rows]

    def get_by_id(self, employee_id: str) -> Employee | None:
        rows = self._client.request(
            "GET",
            "employees",
            query={"select": "*", "employee_id": f"eq.{employee_id}", "limit": "1"},
        )
        return self._deserialize(rows[0]) if rows else None

    def create(self, employee: Employee) -> Employee:
        payload = self._serialize(employee)
        if employee.employee_id:
            payload["employee_id"] = employee.employee_id
        try:
            rows = self._client.request(
                "POST", "employees", payload=payload, prefer="return=representation"
            )
        except SupabaseRequestError as error:
            if error.code == "23505" and "employees_name_unique_ci" in str(error):
                raise DuplicateEmployeeError(
                    f"an employee named {employee.name!r} is already enrolled"
                ) from error
            if error.code == "23505":
                raise DuplicateEmployeeError(
                    "employee name or ID already exists"
                ) from error
            raise
        if len(rows) != 1:
            raise SupabaseRequestError("Supabase did not return the created employee")
        created = self._deserialize(rows[0])
        logger.info("Employee persisted to Supabase | employee_id=%s", created.employee_id)
        return created

    @staticmethod
    def _serialize(employee: Employee) -> dict[str, object]:
        encoding = np.asarray(employee.face_encoding, dtype=np.float64)
        if encoding.shape != (128,) or not np.isfinite(encoding).all():
            raise ValueError("face encoding must contain 128 finite values")
        return {
            "name": employee.name,
            "image_filename": employee.image_filename,
            "face_encoding": encoding.tolist(),
            "created_at": employee.created_at.isoformat(),
        }

    @staticmethod
    def _deserialize(row: dict[str, object]) -> Employee:
        encoding = np.asarray(row["face_encoding"], dtype=np.float64)
        if encoding.shape != (128,) or not np.isfinite(encoding).all():
            raise ValueError(f"stored encoding for {row.get('employee_id')!r} is invalid")
        return Employee(
            employee_id=str(row["employee_id"]),
            name=str(row["name"]),
            image_filename=str(row["image_filename"]),
            face_encoding=encoding,
            created_at=datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")),
        )

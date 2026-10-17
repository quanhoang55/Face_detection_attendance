import unittest
from datetime import date, datetime, timezone
from unittest.mock import Mock

import numpy as np

from backend.models.domain import Employee
from backend.repositories.attendance_supabase import AttendanceSupabaseRepository
from backend.repositories.employee_csv import DuplicateEmployeeError
from backend.repositories.employee_supabase import EmployeeSupabaseRepository
from backend.repositories.supabase_rest import SupabaseRequestError


class SupabaseRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Mock()

    @staticmethod
    def employee_row(employee_id: str = "emp_017") -> dict[str, object]:
        return {
            "employee_id": employee_id,
            "name": "Alice",
            "image_filename": "alice.jpg",
            "face_encoding": np.arange(128, dtype=np.float64).tolist(),
            "created_at": "2026-10-01T10:00:00+00:00",
        }

    def test_create_uses_generated_id_and_returns_encoding(self) -> None:
        self.client.request.return_value = [self.employee_row()]
        repository = EmployeeSupabaseRepository(self.client)
        candidate = Employee(
            employee_id="",
            name="Alice",
            image_filename="alice.jpg",
            face_encoding=np.arange(128, dtype=np.float64),
            created_at=datetime(2026, 10, 1, 10, tzinfo=timezone.utc),
        )

        saved = repository.create(candidate)

        self.assertEqual(saved.employee_id, "emp_017")
        np.testing.assert_array_equal(saved.face_encoding, candidate.face_encoding)
        payload = self.client.request.call_args.kwargs["payload"]
        self.assertNotIn("employee_id", payload)
        self.assertEqual(len(payload["face_encoding"]), 128)

    def test_database_unique_violation_maps_to_duplicate_employee(self) -> None:
        self.client.request.side_effect = SupabaseRequestError(
            'duplicate key violates "employees_name_unique_ci"', code="23505", status=409
        )
        repository = EmployeeSupabaseRepository(self.client)
        candidate = Employee(
            employee_id="",
            name="Alice",
            image_filename="alice.jpg",
            face_encoding=np.zeros(128),
            created_at=datetime.now(timezone.utc),
        )
        with self.assertRaises(DuplicateEmployeeError):
            repository.create(candidate)

    def test_attendance_duplicate_returns_false(self) -> None:
        self.client.request.side_effect = [[{"employee_id": "emp_001"}], []]
        repository = AttendanceSupabaseRepository(self.client)
        when = datetime(2026, 10, 1, 9, tzinfo=timezone.utc)

        self.assertTrue(repository.mark_arrived("emp_001", when, 0.2))
        self.assertFalse(repository.mark_arrived("emp_001", when, 0.2))
        self.assertEqual(
            self.client.request.call_args.kwargs["prefer"],
            "resolution=ignore-duplicates,return=representation",
        )

    def test_attendance_date_is_converted_to_domain_model(self) -> None:
        self.client.request.return_value = [
            {
                "attendance_date": "2026-10-01",
                "employee_id": "emp_001",
                "is_arrive": True,
                "arrived_at": "2026-10-01T09:00:00+00:00",
                "last_distance": 0.2,
            }
        ]
        rows = AttendanceSupabaseRepository(self.client).list_for_date(date(2026, 10, 1))
        self.assertEqual(rows[0].employee_id, "emp_001")
        self.assertTrue(rows[0].is_arrive)


if __name__ == "__main__":
    unittest.main()

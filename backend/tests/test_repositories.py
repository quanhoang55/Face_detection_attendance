import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from backend.models.domain import Employee
from backend.repositories.attendance_csv import AttendanceCsvRepository
from backend.repositories.employee_csv import (
    DuplicateEmployeeError,
    EmployeeCsvRepository,
)


class CsvRepositoryTests(unittest.TestCase):
    def test_employee_encoding_round_trip_and_duplicate_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = EmployeeCsvRepository(Path(directory) / "employees.csv")
            employee = Employee(
                employee_id="emp_001",
                name="Alice",
                image_filename="alice.jpg",
                face_encoding=np.arange(128, dtype=np.float64),
                created_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
            )

            repository.create(employee)
            stored = repository.get_by_id("emp_001")

            self.assertIsNotNone(stored)
            np.testing.assert_array_equal(stored.face_encoding, employee.face_encoding)
            self.assertEqual(repository.next_id(), "emp_002")
            with self.assertRaises(DuplicateEmployeeError):
                repository.create(employee)

            raw_row = (Path(directory) / "employees.csv").read_text()
            self.assertIn(json.dumps(employee.face_encoding.tolist()), raw_row)

    def test_attendance_preserves_first_arrival(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = AttendanceCsvRepository(Path(directory) / "attendance.csv")
            first = datetime(2026, 10, 4, 8, 0, tzinfo=timezone.utc)
            second = datetime(2026, 10, 4, 9, 0, tzinfo=timezone.utc)

            self.assertTrue(repository.mark_arrived("emp_001", first, 0.4))
            self.assertFalse(repository.mark_arrived("emp_001", second, 0.3))

            records = repository.list_for_date(date(2026, 10, 4))
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].arrived_at, first)
            self.assertEqual(records[0].last_distance, 0.4)


if __name__ == "__main__":
    unittest.main()

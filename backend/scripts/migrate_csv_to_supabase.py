"""Validate and import the current CSV database into Supabase.

Run from backend/. The default is a read-only dry run; pass --apply to write.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from datetime import date, datetime
from pathlib import Path

from backend.repositories.supabase_rest import SupabaseRestClient, SupabaseRequestError


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def validate_sources(data_dir: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    employees: list[dict[str, object]] = []
    employee_ids: set[str] = set()
    employee_names: set[str] = set()
    for line, row in enumerate(read_csv(data_dir / "employees.csv"), start=2):
        try:
            employee_id = row["employee_id"].strip()
            name = " ".join(row["name"].split())
            filename = row["image_filename"]
            encoding = json.loads(row["face_encoding"])
            created_at = datetime.fromisoformat(row["created_at"])
            if not employee_id or not name or not filename:
                raise ValueError("employee ID, name, and image filename are required")
            if employee_id in employee_ids:
                raise ValueError(f"duplicate employee ID {employee_id!r}")
            normalized = name.casefold()
            if normalized in employee_names:
                raise ValueError(f"duplicate normalized employee name {name!r}")
            if not isinstance(encoding, list) or len(encoding) != 128:
                raise ValueError("face encoding must contain exactly 128 values")
            numbers = [float(item) for item in encoding]
            if not all(math.isfinite(item) for item in numbers):
                raise ValueError("face encoding values must be finite")
            employee_ids.add(employee_id)
            employee_names.add(normalized)
            employees.append(
                {
                    "employee_id": employee_id,
                    "name": name,
                    "image_filename": filename,
                    "face_encoding": numbers,
                    "created_at": created_at.isoformat(),
                }
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"employees.csv line {line}: {error}") from error

    attendance: list[dict[str, object]] = []
    seen_days: set[tuple[str, str]] = set()
    for line, row in enumerate(read_csv(data_dir / "attendance.csv"), start=2):
        try:
            attendance_date = date.fromisoformat(row["attendance_date"])
            employee_id = row["employee_id"].strip()
            is_arrive = row["is_arrive"].casefold()
            arrived_at = datetime.fromisoformat(row["arrived_at"])
            distance = float(row["last_distance"])
            key = (attendance_date.isoformat(), employee_id)
            if employee_id not in employee_ids:
                raise ValueError(f"unknown employee ID {employee_id!r}")
            if is_arrive not in {"true", "false"}:
                raise ValueError("is_arrive must be true or false")
            if not math.isfinite(distance) or distance < 0:
                raise ValueError("last_distance must be a finite non-negative number")
            if key in seen_days:
                raise ValueError(f"duplicate attendance key {key!r}")
            seen_days.add(key)
            attendance.append(
                {
                    "attendance_date": attendance_date.isoformat(),
                    "employee_id": employee_id,
                    "is_arrive": is_arrive == "true",
                    "arrived_at": arrived_at.isoformat(),
                    "last_distance": distance,
                }
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"attendance.csv line {line}: {error}") from error
    return employees, attendance


def same_employee(existing: dict[str, object], source: dict[str, object]) -> bool:
    return (
        existing.get("employee_id") == source["employee_id"]
        and " ".join(str(existing.get("name", "")).split()).casefold()
        == str(source["name"]).casefold()
        and existing.get("image_filename") == source["image_filename"]
        and np_encoding_equal(existing.get("face_encoding"), source["face_encoding"])
        and datetime.fromisoformat(str(existing["created_at"]).replace("Z", "+00:00"))
        == datetime.fromisoformat(str(source["created_at"]).replace("Z", "+00:00"))
    )


def np_encoding_equal(left: object, right: object) -> bool:
    try:
        return [float(value) for value in left] == [float(value) for value in right]  # type: ignore[union-attr]
    except (TypeError, ValueError):
        return False


def same_attendance(existing: dict[str, object], source: dict[str, object]) -> bool:
    return all(
        str(existing.get(field)) == str(source[field])
        for field in ("attendance_date", "employee_id", "is_arrive", "last_distance")
    ) and datetime.fromisoformat(str(existing["arrived_at"]).replace("Z", "+00:00")) == datetime.fromisoformat(
        str(source["arrived_at"]).replace("Z", "+00:00")
    )


def migrate(data_dir: Path, apply: bool) -> int:
    employees, attendance = validate_sources(data_dir)
    print(f"Validated {len(employees)} employees and {len(attendance)} attendance rows.")
    if not apply:
        print("Dry run only. Re-run with --apply to import these records.")
        return 0

    url = os.getenv("SUPABASE_URL")
    secret = os.getenv("SUPABASE_SECRET_KEY")
    if not url or not secret:
        raise ValueError("SUPABASE_URL and SUPABASE_SECRET_KEY are required with --apply")
    client = SupabaseRestClient(url, secret)
    existing_employees = {
        str(row["employee_id"]): row
        for row in client.request("GET", "employees", query={"select": "*"})
    }
    existing_attendance = {
        (str(row["attendance_date"]), str(row["employee_id"])): row
        for row in client.request("GET", "attendance", query={"select": "*"})
    }

    imported = skipped = failed = 0
    imported_ids: set[str] = set()
    for employee in employees:
        existing = existing_employees.get(str(employee["employee_id"]))
        if existing:
            if same_employee(existing, employee):
                skipped += 1
                imported_ids.add(str(employee["employee_id"]))
                continue
            print(f"CONFLICT employee ID {employee['employee_id']}: existing data differs")
            failed += 1
            continue
        name_collision = next(
            (
                row for row in existing_employees.values()
                if " ".join(str(row.get("name", "")).split()).casefold()
                == str(employee["name"]).casefold()
            ),
            None,
        )
        if name_collision:
            print(f"CONFLICT employee name {employee['name']!r}: already belongs to {name_collision['employee_id']}")
            failed += 1
            continue
        try:
            inserted = client.request(
                "POST", "employees", payload=employee, prefer="return=representation"
            )
            if len(inserted) != 1:
                raise SupabaseRequestError("insert did not return a row")
            imported += 1
            imported_ids.add(str(employee["employee_id"]))
        except SupabaseRequestError as error:
            print(f"FAILED employee {employee['employee_id']}: {error}")
            failed += 1

    for row in attendance:
        key = (str(row["attendance_date"]), str(row["employee_id"]))
        if key[1] not in imported_ids:
            print(f"FAILED attendance {key}: employee was not imported")
            failed += 1
            continue
        existing = existing_attendance.get(key)
        if existing:
            if same_attendance(existing, row):
                skipped += 1
            else:
                print(f"CONFLICT attendance {key}: existing values differ")
                failed += 1
            continue
        try:
            inserted = client.request(
                "POST", "attendance", payload=row,
                prefer="resolution=ignore-duplicates,return=representation",
            )
            if inserted:
                imported += 1
            else:
                latest = client.request(
                    "GET", "attendance",
                    query={
                        "select": "*",
                        "attendance_date": f"eq.{key[0]}",
                        "employee_id": f"eq.{key[1]}",
                        "limit": "1",
                    },
                )
                if latest and same_attendance(latest[0], row):
                    skipped += 1
                else:
                    print(f"CONFLICT attendance {key}: concurrent row has different values")
                    failed += 1
        except SupabaseRequestError as error:
            print(f"FAILED attendance {key}: {error}")
            failed += 1

    print(f"Imported: {imported}; skipped: {skipped}; failed/conflicted: {failed}.")
    print("If employee IDs were imported explicitly, synchronize the sequence using backend/supabase/sequence_sync.sql.")
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--apply", action="store_true", help="write records; default is validation-only")
    args = parser.parse_args()
    try:
        status = migrate(args.data_dir, args.apply)
    except (OSError, ValueError, SupabaseRequestError) as error:
        print(f"Migration stopped: {error}", file=sys.stderr)
        status = 1
    raise SystemExit(status)


if __name__ == "__main__":
    main()

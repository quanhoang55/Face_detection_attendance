# Supabase Implementation Plan

## Target architecture

```text
Vercel React frontend
        │ HTTPS (FastAPI API only)
        ▼
Render FastAPI backend
        │ Supabase server-side secret key
        ▼
Supabase PostgreSQL
```

The frontend continues to call the existing FastAPI endpoints. It must never
access employee face encodings or attendance tables directly. Face detection,
encoding, and matching remain in the Python backend.

## Decisions and scope

- Use Supabase PostgreSQL for production persistence.
- Keep CSV repositories for local development and as a migration/rollback
  source until production is verified.
- Use Supabase's HTTPS Data API from the backend. The current implementation
  uses a small standard-library REST client, so it does not need an additional
  Supabase SDK dependency. The database password is not needed by the running
  backend; keep it for dashboard, CLI, or direct PostgreSQL administration.
- Keep face encodings as PostgreSQL `double precision[]`. The current system
  has a small employee set, so database-side vector search is not needed.
- Do not use Supabase Storage unless retaining original employee images becomes
  a requirement. The app currently only needs the uploaded image to calculate
  an encoding.

## Supabase setup

### 1. Create a project and obtain credentials

Create a Supabase project in a region close to the Render backend. Save the
database password securely, then copy the project URL and a new secret API key
(`sb_secret_...`) from the API Keys settings:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SECRET_KEY=sb_secret_xxxxxxxxx
```

The secret key belongs only in Render's environment settings. It bypasses Row
Level Security, so never add it to Vercel, browser code, Git, or a `VITE_*`
variable. Use a publishable key only for a separately designed browser access
flow with authentication and strict RLS; this app does not need one.

Supabase API key guidance:
https://supabase.com/docs/guides/getting-started/api-keys

### 2. Create the initial database schema

For a brand-new project, run this SQL in the Supabase SQL Editor. Treat it as
the initial schema, not as a general upgrade script: `IF NOT EXISTS` will not
retrofit missing constraints on tables that already exist. If any of these
tables already exist, inspect them and apply explicit `ALTER TABLE` migrations
instead of assuming this script upgraded them.

```sql
create sequence if not exists employee_number_seq start with 1;

create or replace function public.generate_employee_id()
returns text language sql volatile as $$
    select 'emp_' || case
        when value < 1000 then lpad(value::text, 3, '0')
        else value::text
    end
    from (select nextval('public.employee_number_seq') as value) generated;
$$;

create table if not exists public.employees (
    employee_id text primary key default public.generate_employee_id(),
    name text not null,
    image_filename text not null,
    face_encoding double precision[] not null,
    created_at timestamptz not null default now(),
    constraint employee_name_not_empty check (length(trim(name)) > 0),
    constraint face_encoding_has_128_values
        check (cardinality(face_encoding) = 128)
);

create unique index if not exists employees_name_unique_ci
    on public.employees (lower(trim(name)));

create table if not exists public.attendance (
    attendance_date date not null,
    employee_id text not null
        references public.employees(employee_id) on delete cascade,
    is_arrive boolean not null default true,
    arrived_at timestamptz not null,
    last_distance double precision not null,
    constraint attendance_employee_day_pk
        primary key (attendance_date, employee_id)
);

create index if not exists attendance_employee_id_index
    on public.attendance (employee_id);

alter table public.employees enable row level security;
alter table public.attendance enable row level security;

revoke all on table public.employees from anon, authenticated;
revoke all on table public.attendance from anon, authenticated;
grant all on table public.employees to service_role;
grant all on table public.attendance to service_role;
grant usage, select on sequence public.employee_number_seq to service_role;
grant execute on function public.generate_employee_id() to service_role;
```

The composite attendance key enforces one arrival per employee per date, even
if two camera requests arrive at the same time. The case-insensitive unique
index is the final authority on duplicate employee names.

### 3. Verify grants and API exposure

Keep RLS enabled and do not add public policies for these tables. Confirm that
`anon` and `authenticated` have no table privileges. Grants and RLS are
separate controls; verify both in the SQL editor or dashboard. The backend
secret key has the elevated access required by the API.

Supabase security guidance:
https://supabase.com/docs/guides/database/secure-data

## Backend implementation phases

### Phase 1: Configuration and client

Add these settings to `backend/src/backend/config.py`:

```env
STORAGE_BACKEND=csv
SUPABASE_URL=
SUPABASE_SECRET_KEY=
```

`STORAGE_BACKEND` accepts `csv` or `supabase`. Keep `csv` as the local default.
When `supabase` is selected, validate that the URL and secret key are present
at startup and fail with a clear configuration error if either is missing.

Add `backend/.env.example` with empty credential values. Ensure real `.env`
files are ignored by Git. Do not log the secret key.

### Phase 2: Build a reusable client

The implemented client uses the standard library to call PostgREST and holds
the URL/key for the application lifetime. Keep it injectable so repository
tests can supply a mock client. If replacing it with the official Supabase
Python SDK later, verify the same request/response behavior in tests first.

### Phase 3: Keep repository boundaries

Keep face recognition and business logic in the existing services. Add
Supabase-backed implementations while preserving the behavior needed by the
services:

```text
repositories/
├── employee_csv.py
├── attendance_csv.py
├── employee_supabase.py
└── attendance_supabase.py
```

Employee operations include `list_all()`, `get_by_id()`, and `create()`. Name
uniqueness is enforced by the database; an optional pre-check can improve the
message but must not be treated as race-safe. Attendance operations include
`list_for_date()` and `mark_arrived()`.

Select both repository types in `create_core()` using `STORAGE_BACKEND`. The
services should depend on repository interfaces or compatible protocols rather
than concrete CSV classes. Preserve the existing HTTP API schemas and routes.

### Phase 4: Database-generated employee IDs

Remove `next_id()` from the service enrollment flow. Build the employee
candidate from the normalized name, source filename, encoding, and timestamp,
then let `EmployeeSupabaseRepository.create()` omit `employee_id` from the
insert and return the inserted row with its database-generated ID.

The CSV repository can retain its local ID-generation behavior behind the same
repository contract. Do not generate IDs in application memory for Supabase;
that can collide under simultaneous enrollments.

### Phase 5: Encode/decode face vectors

Before inserting, serialize NumPy values as a JSON-compatible list:

```python
encoding.tolist()
```

When reading a row, validate and convert it:

```python
encoding = np.asarray(row["face_encoding"], dtype=np.float64)
if encoding.shape != (128,):
    raise InvalidKnownFaceError("stored encoding must have 128 values")
```

Do not log the vector itself. The column remains a PostgreSQL
`double precision[]`; no `pgvector` extension is needed for the current
in-memory matching flow.

### Phase 6: Handle duplicate names and atomic attendance

Map the database unique violation for the normalized/case-insensitive name
index to the existing duplicate employee domain error, which the API maps to
HTTP 409. Do not rely only on a prior `name_exists()` check because concurrent
requests can pass that check together.

Attendance writes must use the composite key and duplicate-safe insert
semantics equivalent to:

```sql
insert into public.attendance (...)
values (...)
on conflict (attendance_date, employee_id) do nothing;
```

With the Supabase Data API, use the Python client's supported `upsert` or
insert/conflict options, and verify the response semantics in a focused test.
The repository must return `True` only when this request created the row and
`False` when today's row already existed. Do not implement attendance as a
separate read followed by write.

For employee inserts, confirm that the client request returns the inserted
row, including generated `employee_id`. If it does not, use the documented
return-representation option or a follow-up query by a stable unique key. Do
not guess the generated ID.

### Phase 7: Migrate CSV data safely

Create `backend/scripts/migrate_csv_to_supabase.py`. It must be safe to rerun:

1. Read and validate all employee rows before sending writes. Require unique
   IDs and names, valid timestamps, and exactly 128 finite numeric encoding
   values per employee.
2. Read attendance rows and validate dates, timestamps, employee references,
   numeric distances, and boolean values.
3. Insert employees while preserving IDs such as `emp_001`. Use an explicit
   conflict policy: skip an identical existing row, and stop with a clear error
   if an existing ID or normalized name contains different data.
4. Insert attendance rows with duplicate-safe semantics. Treat an identical
   existing employee/date row as skipped; report conflicting values for
   review instead of silently overwriting them.
5. Print imported, skipped, and failed counts without printing face encodings
   or secrets. Return a nonzero exit code if any row failed or conflicted.
6. Never delete or modify the source CSV files.

Back up both CSV files before migration. Run the migration with credentials
provided through environment variables or a local ignored `.env` file:

```bash
cd backend
SUPABASE_URL="https://your-project.supabase.co" \
SUPABASE_SECRET_KEY="sb_secret_xxx" \
uv run python scripts/migrate_csv_to_supabase.py
```

The migration inserts historical IDs explicitly, so PostgreSQL's sequence
must be advanced afterward. After importing employees, run this in the SQL
Editor (or have a migration function do the same) to set the next generated ID
above the largest imported `emp_NNN` value:

```sql
select setval(
    'public.employee_number_seq',
    greatest(
        coalesce((
            select max(substring(employee_id from '^emp_([0-9]+)$')::bigint)
            from public.employees
            where employee_id ~ '^emp_[0-9]+$'
        ), 0),
        1
    ),
    exists (select 1 from public.employees where employee_id ~ '^emp_[0-9]+$')
);
```

Verify that the next employee created receives an unused ID before allowing
normal enrollment. Sequence synchronization is required even when importing
only one existing employee.

### Phase 8: Tests and live verification

Add mocked-client repository tests for:

- Insert returning a database-generated employee ID.
- Name conflict mapping, including concurrent/unique-violation behavior.
- Read and validation of face encodings.
- Employee list and lookup behavior.
- Attendance insert returning `True` once and `False` on conflict.
- Attendance date filtering.
- Database/network error translation and logging without credentials or
  encodings.
- Migration validation, idempotent skips, conflicts, and sequence-sync SQL.

Keep existing face encoder and recognizer unit tests. Add an integration test
against a dedicated non-production Supabase project or schema to confirm real
Data API response behavior, generated-ID return behavior, unique-violation
mapping, and duplicate attendance semantics. Never run migration or integration
tests against production by default.

## Render configuration

Set these environment variables on the Render backend:

```env
STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SECRET_KEY=sb_secret_xxxxxxxxx
FACE_TIMEZONE=Asia/Ho_Chi_Minh
FACE_LOG_LEVEL=INFO
FACE_CORS_ORIGINS=https://your-frontend.vercel.app
```

Use the Render start command:

```bash
uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port $PORT
```

Once the backend is confirmed to use Supabase, the persistent disk is no
longer needed for CSV data. Keep one backend instance during the CSV transition
and do not run two application versions against CSV simultaneously.

## Vercel configuration

Set only the backend's public URL in the Vercel frontend project:

```env
VITE_API_URL=https://your-backend.onrender.com
```

Never set `SUPABASE_SECRET_KEY`, the database password, or face encodings in
Vercel. `VITE_*` variables are included in browser-delivered frontend code.

## Tests and deployment order

1. Back up `employees.csv` and `attendance.csv` to a secure location outside
   the repository. Face encodings are sensitive biometric data.
2. Create Supabase project and credentials.
3. Apply the initial schema and verify RLS, grants, indexes, and constraints.
4. Add configuration, client factory, repositories, and backend tests.
5. Test against a dedicated non-production Supabase project.
6. Run the migration in dry-run/validation mode and review its report.
7. Run the migration and synchronize the employee ID sequence.
8. Compare employee and attendance row counts against both CSV files; inspect
   representative records without exposing their encodings.
9. Test employee listing, enrollment, recognition, attendance creation, and
   duplicate attendance using the Supabase-backed backend.
10. Deploy the Supabase-backed backend to Render and set its environment
    variables.
11. Configure CORS on Render and `VITE_API_URL` on Vercel, then deploy the
    frontend.
12. Monitor logs and verify successful reads/writes after deployment.
13. Retain the source CSV backups and migration report until production has
    been stable and a separate backup is verified.

## Rollback plan

Keep the previous Render deployment and the original CSV backups. If the
Supabase-backed service fails before accepting production writes, set
`STORAGE_BACKEND=csv` and redeploy using a persistent Render disk with
`FACE_DATA_DIR` pointing to the restored CSV directory.

If Supabase has already accepted new production writes, do not switch directly
to the old CSV snapshot or those writes will disappear from the application.
Export the current Supabase rows back to CSV (or otherwise reconcile all
post-migration changes), verify row counts and IDs, then switch the backend.
Never delete the Supabase project or source CSV backups as part of rollback.

## Limitations and operational notes

- Supabase Free projects may pause after a period of low activity. Review the
  current plan limits and maintain off-site exports for important data.
- Face encodings are biometric data. Limit access, avoid logging them, and
  define retention/deletion rules before using real employees.
- The current API has no authentication. Before making it publicly available,
  add authentication and authorization to enrollment, attendance, and employee
  listing endpoints.
- CSV remains a local-development option; Supabase is the production store.

# Face Recognition Attendance API

The Python package uses a `src/` layout. Pass that source directory to Uvicorn
explicitly so application imports also work in reload subprocesses.

From the `backend/` directory:

```bash
uv sync
uv run uvicorn --app-dir src backend.main:app --reload
```

From the repository root:

```bash
uv sync --project backend
uv run --project backend uvicorn --app-dir backend/src backend.main:app --reload
```

The API is served at <http://127.0.0.1:8000> and its interactive documentation
is available at <http://127.0.0.1:8000/docs>.

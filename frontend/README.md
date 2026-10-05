# Face Recognition Attendance Frontend

React and TypeScript frontend for employee enrollment and camera attendance.

## Run locally

Start the backend from the repository root:

```bash
uv run --project backend uvicorn --app-dir backend/src backend.main:app --reload
```

In another terminal, start the frontend:

```bash
cd frontend
bun install
bun run dev
```

Open <http://localhost:5173>.

The frontend uses `http://127.0.0.1:8000` by default. To use another backend URL,
create a `.env.local` file:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Camera access works on localhost or HTTPS and requires browser permission.

## Checks

```bash
bun run lint
bun run build
```

# STACK — Local QR + Seven-Segment Digit Detection System

## 1. Stack Overview

The application is a local computer-vision system composed of four main layers:

```text
┌─────────────────────────────────────────────┐
│                  Frontend                   │
│            TypeScript + React               │
└──────────────────────┬──────────────────────┘
                       │
                       │ HTTP / WebSocket
                       ▼
┌─────────────────────────────────────────────┐
│                  Backend                    │
│         Python + FastAPI + Pydantic         │
└──────────────────────┬──────────────────────┘
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
┌──────────────────────┐  ┌──────────────────┐
│ Computer Vision      │  │ Database         │
│ YOLO + QR Decoder    │  │ txt/csv/Supabase │
└──────────────────────┘  └──────────────────┘
```

The architecture should remain modular so individual technologies can be replaced later without changing the entire application.

---

# 2. Frontend Stack

## 2.1 Core

### TypeScript

TypeScript is the primary language for the frontend.

Responsibilities:

- Type-safe application logic.
- API response types.
- WebSocket message types.
- Component props.
- UI state.
- Frontend domain models.

Example:

```ts
interface RecognitionResult {
    qrData: string | null;
    rawDigits: string | null;
    numericValue: number | null;
    confidence: number | null;
    status: RecognitionStatus;
}
```

---

## 2.2 React

React is the frontend framework.

Responsibilities:

- UI rendering.
- Component architecture.
- Application state integration.
- Camera display.
- Detection overlay.
- Recognition result display.
- Save interaction.
- Recent-record display.

The frontend should be component-oriented rather than placing the entire application in one component.

Suggested structure:

```text
src/
├── components/
│   ├── CameraView/
│   ├── DetectionOverlay/
│   ├── RecognitionPanel/
│   ├── SaveButton/
│   ├── StatusIndicator/
│   └── RecentRecords/
│
├── services/
│   ├── api.ts
│   └── websocket.ts
│
├── hooks/
│   ├── useRecognition.ts
│   └── useMeasurements.ts
│
├── types/
│   ├── recognition.ts
│   └── measurement.ts
│
└── App.tsx
```

---

# 3. Frontend Communication

The frontend communicates with the local backend through two main mechanisms.

## HTTP / REST

Used for request-response operations:

```text
GET  /health
GET  /measurements
POST /measurements
```

Primary use:

- Saving measurements.
- Retrieving recent records.
- Health checks.
- Configuration endpoints if needed.

---

## WebSocket

Used for real-time recognition information.

Example:

```text
Backend
   │
   │ WebSocket
   ▼
Frontend
```

Possible events:

```text
camera_status
detection
recognition
error
```

Example message:

```json
{
    "type": "recognition",
    "qrData": "DEVICE-001",
    "rawDigits": "1250",
    "numericValue": 12.5,
    "confidence": 0.91,
    "status": "READY_TO_SAVE"
}
```

---

# 4. Backend Stack

## 4.1 Python

Python is the primary backend language.

Reasons:

- Strong computer-vision ecosystem.
- Strong ML ecosystem.
- Easy integration with YOLO.
- Easy integration with OpenCV.
- Fast development for the local prototype.
- Good support for scientific and numerical processing.

Python will contain the CV pipeline and API server.

---

# 5. FastAPI

FastAPI is the backend web framework.

Responsibilities:

- HTTP API.
- WebSocket API.
- Request handling.
- Response serialization.
- Application lifecycle.
- Dependency injection.
- Error handling.

Example architecture:

```text
FastAPI
   │
   ├── REST API
   │
   ├── WebSocket
   │
   └── Application Services
```

FastAPI should not contain the computer-vision business logic directly inside route functions.

Prefer:

```text
Route
  ↓
Service
  ↓
CV / Repository
```

rather than:

```text
Route
  ↓
Everything
```

---

# 6. Pydantic

Pydantic is used for data validation and serialization.

Responsibilities:

- API request models.
- API response models.
- Recognition result models.
- Configuration models.
- Validation of application data.

Example:

```python
from pydantic import BaseModel


class RecognitionResult(BaseModel):
    qr_data: str | None
    raw_digits: str | None
    numeric_value: float | None
    confidence: float | None
    status: str
```

Pydantic models should define the contracts between components.

---

# 7. Computer Vision Stack

## 7.1 Ultralytics YOLO

The seven-segment digit detector uses YOLO.

Responsibilities:

- Load trained weights.
- Run inference.
- Detect individual digits.
- Return bounding boxes.
- Return class IDs.
- Return confidence scores.

Initial classes:

```text
0
1
2
3
4
5
6
7
8
9
```

The YOLO model is only responsible for detection.

It should not be responsible for:

- QR decoding.
- Database writes.
- API responses.
- UI rendering.
- Recognition persistence.

---

# 8. OpenCV

OpenCV is used for image and camera processing.

Potential responsibilities:

- Camera capture.
- Frame manipulation.
- Image resizing.
- Color conversion.
- Cropping.
- Preprocessing.
- Debug image generation.
- QR decoding if OpenCV's QR detector is selected.

Possible camera pipeline:

```text
Camera
  ↓
OpenCV
  ↓
Frame
  ↓
YOLO / QR Decoder
```

OpenCV should remain inside the backend/CV layer.

---

# 9. QR Decoder

QR recognition should be implemented using a dedicated QR-decoding library.

Possible initial choice:

```text
OpenCV QRCodeDetector
```

Alternative libraries can be evaluated later if recognition reliability is insufficient.

The QR component should expose a small interface:

```python
decode(frame) -> QRResult | None
```

The rest of the application should not depend directly on the QR library.

---

# 10. NumPy

NumPy is used for numerical image processing and model input/output.

Responsibilities:

- Image arrays.
- Tensor preparation.
- Bounding-box calculations.
- Coordinate calculations.
- Frame manipulation.
- Numerical operations.

Example:

```text
Camera Frame
     ↓
NumPy Array
     ↓
Preprocessing
     ↓
YOLO
```

---

# 11. PyTorch

PyTorch is the ML runtime underlying the training/inference ecosystem where required by the selected YOLO implementation.

Primary use:

```text
Model
  ↓
PyTorch runtime
  ↓
Inference
```

Training may be performed separately in Google Colab.

The production/local application should use the exported inference model/runtime appropriate for the deployment environment if that provides better performance.

---

# 12. Model Training Environment

Training should be separated from the local application.

Recommended workflow:

```text
Google Colab
    │
    ├── Dataset
    ├── YOLO Training
    ├── Validation
    └── Model Export
             │
             ▼
       Trained Model
             │
             ▼
       Local Application
```

The local application should not need to train the model.

The local application only needs to load and run the trained model.

---

# 13. Database

The database decision is intentionally deferred.

Two candidates are currently being considered:

```text
Option A:
txt, csv (one file) (this system is local)

Option B:
Supabase / PostgreSQL
```

No database implementation should be built yet.

The architecture should first define a database-independent persistence interface.

For example:

```python
class MeasurementRepository:
    def create(self, measurement):
        ...

    def get_recent(self, limit):
        ...
```

The CV and API layers should depend on the repository interface rather than directly depending on Supabase or MongoDB.

---

# 14. Why Database Is Deferred

The core system can be developed and tested without finalizing the database.

Initial development should focus on:

```text
Camera
   ↓
QR
   ↓
Seven-Segment Detection
   ↓
Recognition
   ↓
Frontend
   ↓
Save Request
```

Database integration comes afterward.

During early development, a temporary in-memory or local persistence implementation can be used if required.

Example:

```text
RecognitionResult
       ↓
Temporary Repository
       ↓
Local Testing
```

Later:

```text
RecognitionResult
       ↓
Repository Interface
       ↓
Supabase / PostgreSQL
```

or:

```text
RecognitionResult
       ↓
Repository Interface
       ↓
MongoDB
```

---

# 15. Database Abstraction

The application should use a repository layer.

Recommended architecture:

```text
FastAPI Route
      ↓
Measurement Service
      ↓
Measurement Repository
      ↓
Database
```

The service should not contain database-specific queries.

Bad:

```python
@app.post("/measurements")
async def save_measurement(...):
    # Supabase query directly here
```

Preferred:

```python
@app.post("/measurements")
async def save_measurement(...):
    return await measurement_service.save(...)
```

Then:

```text
MeasurementService
       ↓
MeasurementRepository
       ↓
Concrete Database Implementation
```

---

# 16. Application Layers

The complete backend can be organized into:

```text
backend/
│
├── api/
│   ├── routes/
│   └── websocket/
│
├── services/
│   ├── recognition_service.py
│   └── measurement_service.py
│
├── cv/
│   ├── camera.py
│   ├── qr_detector.py
│   ├── digit_detector.py
│   ├── digit_processor.py
│   └── stabilizer.py
│
├── schemas/
│   ├── recognition.py
│   └── measurement.py
│
├── repositories/
│   └── measurement.py
│
├── database/
│   └── ...
│
├── config/
│   └── settings.py
│
└── main.py
```

The exact structure can evolve during implementation.

---

# 17. Core Backend Data Flow

```text
Camera
  ↓
Frame Capture
  ↓
CV Pipeline
  ├── QR Decoder
  └── Digit Detector
          ↓
      Post-processing
          ↓
      Recognition Result
          ↓
      Stabilization
          ↓
      FastAPI WebSocket
          ↓
       Frontend
```

When the user presses Save:

```text
Frontend
   │
   │ POST /measurements
   ▼
FastAPI
   │
   ▼
Measurement Service
   │
   ▼
Repository
   │
   ▼
Database
```

---

# 18. Suggested API

Initial API:

```text
GET  /health
GET  /measurements
POST /measurements
```

WebSocket:

```text
WS /ws/recognition
```

Possible future endpoints:

```text
GET    /measurements/{id}
DELETE /measurements/{id}
GET    /camera/status
POST   /camera/reconnect
GET    /config
```

These should only be added when required.

---

# 19. API Contracts

## POST /measurements

Request:

```json
{
    "qr_data": "DEVICE-001",
    "raw_digits": "1250",
    "numeric_value": 12.5,
    "confidence": 0.91
}
```

Response:

```json
{
    "id": 42,
    "qr_data": "DEVICE-001",
    "raw_digits": "1250",
    "numeric_value": 12.5,
    "confidence": 0.91,
    "created_at": "2026-09-29T12:01:22Z"
}
```

---

# 20. WebSocket Contract

The WebSocket provides live recognition information.

Example:

```json
{
    "type": "recognition",
    "qr_data": "DEVICE-001",
    "raw_digits": "1250",
    "numeric_value": 12.5,
    "confidence": 0.91,
    "status": "READY_TO_SAVE",
    "detections": [
        {
            "class_id": 1,
            "confidence": 0.98,
            "bbox": [120, 150, 40, 80]
        },
        {
            "class_id": 2,
            "confidence": 0.97,
            "bbox": [165, 150, 40, 80]
        }
    ]
}
```

The frontend uses this data to render:

```text
Live camera
+
Bounding boxes
+
Recognition result
+
Status
```

---

# 21. Local Deployment

The application is intended to run on a local machine.

Conceptually:

```text
┌───────────────────────────────┐
│        Local Computer         │
│                               │
│  ┌─────────────────────────┐  │
│  │ React Frontend          │  │
│  └────────────┬────────────┘  │
│               │               │
│  ┌────────────▼────────────┐  │
│  │ FastAPI Backend         │  │
│  │                         │  │
│  │ Camera + CV + API       │  │
│  └────────────┬────────────┘  │
│               │               │
│  ┌────────────▼────────────┐  │
│  │ Database                │  │
│  └─────────────────────────┘  │
│                               │
│          USB Camera           │
└───────────────────────────────┘
```

The frontend can communicate with:

```text
http://localhost:<backend-port>
```

---

# 22. Development Environment

## Frontend

```text
Node.js
TypeScript
React
npm / pnpm
```

## Backend

```text
Python
FastAPI
Pydantic
Uvicorn
```

## Computer Vision

```text
Ultralytics
OpenCV
NumPy
PyTorch
```

## Training

```text
Google Colab
Google Drive
Ultralytics
PyTorch
```

## Database

```text
TBD:
Supabase / PostgreSQL
or
MongoDB
```

---

# 23. Dependency Philosophy

The project should avoid adding libraries without a clear purpose.

Core dependencies should have clear responsibilities:

```text
React
    → UI

TypeScript
    → Type safety

FastAPI
    → HTTP/WebSocket server

Pydantic
    → Data validation

Uvicorn
    → ASGI server

Ultralytics
    → YOLO inference

OpenCV
    → Camera/image processing

NumPy
    → Numerical/image arrays

PyTorch
    → ML runtime

Database driver
    → Added only after database choice
```

The final database dependencies should not be installed until the database architecture is decided.

---

# 24. Technology Boundaries

A major architectural rule is to keep technology-specific code at the edges.

For example:

```text
FastAPI
   ↓
Service
   ↓
Repository Interface
   ↓
Database Implementation
```

not:

```text
FastAPI
   ↓
Supabase-specific code
   ↓
Business logic
```

Similarly:

```text
Recognition Service
   ↓
Digit Detector Interface
   ↓
YOLO Implementation
```

This makes the system easier to test and replace.

---

# 25. Testing Stack

Frontend:

```text
TypeScript type checking
React component tests
API integration tests
```

Backend:

```text
pytest
FastAPI TestClient
Pydantic validation tests
```

CV:

```text
Dataset validation
Model validation
Image-based tests
Camera integration tests
```

Database:

```text
Repository tests
Integration tests
```

The database tests should be added only after the database implementation is selected.

---

# 26. Development Order

The stack should be implemented in this order:

```text
1. Camera
       ↓
2. QR detection
       ↓
3. Seven-segment model
       ↓
4. Digit post-processing
       ↓
5. Combined recognition
       ↓
6. FastAPI recognition service
       ↓
7. React live camera UI
       ↓
8. Detection overlay
       ↓
9. Save API
       ↓
10. Database selection
       ↓
11. Database repository
       ↓
12. Recent records
```

The database is deliberately near the end of the first development cycle.

---

# 27. Final Stack

## Frontend

```text
TypeScript
React
```

Communication:

```text
REST
WebSocket
```

---

## Backend

```text
Python
FastAPI
Pydantic
Uvicorn
```

---

## Computer Vision

```text
Ultralytics YOLO
OpenCV
NumPy
PyTorch
```

---

## Database

```text
TBD

Candidate 1:
Supabase / PostgreSQL

Candidate 2:
MongoDB
```

No database-specific architecture should be finalized yet.

---

# 28. Target Architecture

The intended architecture is:

```text
                         USB CAMERA
                             │
                             ▼
                    ┌─────────────────┐
                    │  Python / OpenCV│
                    └────────┬────────┘
                             │
                  ┌──────────┴──────────┐
                  │                     │
                  ▼                     ▼
             QR Decoder            YOLO Model
                  │                     │
                  └──────────┬──────────┘
                             ▼
                    Recognition Service
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
                WebSocket          Save API
                    │                 │
                    ▼                 ▼
              React Frontend       Service
                                      │
                                      ▼
                                  Repository
                                      │
                                      ▼
                              Database (TBD)
```

The key design decision is to build the **camera + CV + recognition + frontend flow first**, while keeping persistence behind an abstraction.

This allows the project to reach a working end-to-end prototype before committing to either Supabase/PostgreSQL or MongoDB.

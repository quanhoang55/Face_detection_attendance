# Facial Recognition Attendance System — Architecture & Specification

This document details the system design, workflow, data pipelines, and technical specifications for a real-time face recognition attendance system built using Python, OpenCV, and `face_recognition`.

---

## 1. System Overview

The system captures real-time video frames from a camera feed, detects human faces, extracts feature encodings, compares them against a database of known users, and automatically logs attendance records when a verified match is found.

```
                  ┌──────────────────────┐
                  │   Camera / RTSP      │
                  └──────────┬───────────┘
                             │ Video Frames
                             ▼
                  ┌──────────────────────┐
                  │ Frame Preprocessor   │ (Resize, Color Conversion)
                  └──────────┬───────────┘
                             │ Processed Frame
                             ▼
                  ┌──────────────────────┐
                  │   Face Detection     │ (HOG / CNN Model)
                  └──────────┬───────────┘
                             │ Face Bounding Boxes
                             ▼
                  ┌──────────────────────┐
                  │ Feature Extraction   │ (128-d Vector Encoding)
                  └──────────┬───────────┘
                             │ Face Vectors
                             ▼
                  ┌──────────────────────┐
                  │  Vector Matching     │ ◄─── Known Encodings DB
                  └──────────┬───────────┘
                             │ Verified Identity
                             ▼
                  ┌──────────────────────┐
                  │ Attendance Logger    │ (Cooldown & Storage)
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [ Database / CSV ]                [ UI / Display ]
```

---

## 2. Core Operational Workflow

### Phase A: Enrollment & Pre-Processing

1. **Image Ingestion:** Collect clean, high-resolution front-facing photos of users.
2. **Encoding Generation:**
    - Load each image using `face_recognition.load_image_file()`.
    - Extract the 128-dimensional facial embedding vector using `face_recognition.face_encodings()`.
3. **Persistence:** Store vectors alongside user metadata (ID, Name, Department) in memory or a persistent storage format (e.g., Pickle, SQLite, or Vector DB).

### Phase B: Real-Time Detection & Recognition

1. **Frame Acquisition:** Read video frames via `cv2.VideoCapture()`.
2. **Performance Optimization:**
    - Downscale frame dimensions (e.g., scale factor `0.25`) to reduce compute load.
    - Convert image colorspace from **BGR** (OpenCV format) to **RGB** (`face_recognition` requirement).
3. **Detection:** Locate bounding box coordinates (`(top, right, bottom, left)`) using `face_recognition.face_locations()`.
4. **Encoding Extraction:** Calculate 128-d embeddings for all detected faces in the frame.
5. **Euclidean Matching:**
    - Compute Euclidean distances against stored vectors via `face_recognition.face_distance()`.
    - Find the minimum distance index.
    - Verify if distance $\le \text{Tolerance}$ (Default recommended: `0.5`–`0.6`).

### Phase C: Cooldown & Logging Policy

1. **Match Verification:** Check if distance threshold conditions are met.
2. **Cooldown Logic:** Ensure a recognized user is not logged repeatedly within a designated window (e.g., 5-minute threshold) to prevent redundant database writes.
3. **Log Record Creation:** Write `[User ID, Name, Timestamp, Confidence Score]` into CSV or SQL database.

---

## 3. Tech Stack & Dependencies

| Component            | Library / Tool          | Description                                                                  |
| :------------------- | :---------------------- | :--------------------------------------------------------------------------- |
| **Language**         | Python 3.9+             | Primary runtime environment                                                  |
| **Computer Vision**  | `opencv-python` (`cv2`) | Video stream capture, image preprocessing, UI drawing                        |
| **Face Recognition** | `face_recognition`      | Built on top of `dlib` C++ library; handles face location & 128-d embeddings |
| **Math / Matrices**  | `numpy`                 | High-performance vector distance calculations                                |
| **Storage**          | SQLite / CSV / Pandas   | Storage for user records and attendance logs                                 |

---

## 4. Key Performance Optimizations

- **Frame Skipping:** Process face detection every $N^{\text{th}}$ frame (e.g., every 3rd or 4th frame) to maintain target FPS rates on lower-end hardware.
- **Resolution Reduction:** Downscaling resolution during the detection step significantly reduces matrix computation without impacting vector quality.
- **Multi-threading:** Separate video frame capture (`cv2.VideoCapture`) into an asynchronous thread to avoid I/O blocking.

---

## 5. Security & Edge Case Handling

1. **Unknown Persons:** Faces exceeding the distance threshold are flagged as "Unknown" and recorded in an anomaly log for security audit.
2. **Anti-Spoofing (Liveness Detection):** Standard feature vectors do not protect against printed photos or screens. Production deployments should incorporate:
    - Blink detection via facial landmark ratios (EAR - Eye Aspect Ratio).
    - Depth cameras or IR camera sensors.
    - Random challenge-response prompts (e.g., "turn head left").

---

## 6. Database Schema (Example SQLite Structure)

### Users Table

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    department TEXT,
    encoding_data BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Attendance Logs Table

```sql
CREATE TABLE IF NOT EXISTS attendance_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

# Module 5: GPS + GIS Location Verification

> **Student 5 Module**  
> **Final-Year Project**: *Smart Attendance and Field Activity Monitoring System*  
> **Repository Folder**: `module5_gis/`  
> **Technology Stack**: Python, Flask, Requests, TNGIS REST/OGC Web Services, Pytest  

---

## Table of Contents

1. [Module Objective](#1-module-objective)
2. [Project Role Structure](#2-project-role-structure)
3. [System Architecture & Workflow](#3-system-architecture--workflow)
4. [TNGIS Services Implemented](#4-tngis-services-implemented)
5. [API Configuration & Environment Variables](#5-api-configuration--environment-variables)
6. [Project Folder Structure](#6-project-folder-structure)
7. [Installation & Setup](#7-installation--setup)
8. [Running the Module](#8-running-the-module)
9. [Running Automated Tests](#9-running-automated-tests)
10. [Live TNGIS API Integration Test](#10-live-tngis-api-integration-test)
11. [Standardized API Contracts & Examples](#11-standardized-api-contracts--examples)
12. [Integration Contract with Student 2 (Backend API)](#12-integration-contract-with-student-2-backend-api)
13. [Dual-Factor Authentication Flow with Student 4 (AI Face)](#13-dual-factor-authentication-flow-with-student-4-ai-face)
14. [Real TNGIS API Data vs Local Test Data](#14-real-tngis-api-data-vs-local-test-data)
15. [System Limitations & Security Notes](#15-system-limitations--security-notes)

---

## 1. Module Objective

The core objective of **Module 5: GPS + GIS Location Verification** is to provide a tamper-resistant spatial verification mechanism for worker attendance authentication:

> **Verify whether an employee/worker's real GPS coordinates are strictly inside their permitted geographical/workplace boundary using official Tamil Nadu Geographical Information System (TNGIS) spatial services.**

### Core Operations:
1. **GPS Coordinate Validation**: Verify that received latitude and longitude values conform to the WGS 84 coordinate reference system (Latitude $\in [-90.0, 90.0]$, Longitude $\in [-180.0, 180.0]$).
2. **TNGIS Spatial Point-in-Polygon Query**: Dispatch coordinates to the TNGIS `Inside Boundary` service for polygon containment verification against authorized workplace/administrative boundaries.
3. **Geographical Administrative Resolution**: Query TNGIS administrative datasets (District, Taluk, Revenue Village) to obtain verified administrative identifiers.
4. **Structured Decision Output**: Return a clean JSON-serializable status (`VERIFIED`, `REJECTED`, `API_ERROR`, or `VALIDATION_ERROR`) consumable by Student 2's Backend API.

---

## 2. Project Role Structure

This engineering project is partitioned across 6 independent student modules:

| Role | Student | Domain | Integration Boundary |
|---|---|---|---|
| Student 1 | Mobile App | Flutter / Dart | Captures selfie image + device GPS coordinates |
| Student 2 | Backend / API | FastAPI / Flask | Gateway orchestrating attendance logic and DB writes |
| Student 3 | Database & Auth | MySQL / JWT | User accounts, roles, attendance logs |
| Student 4 | AI Biometrics | OpenCV (YuNet + SFace) | 1:1 facial cosine similarity verification |
| **Student 5** | **GPS + GIS (MY MODULE)** | **Python, Flask, TNGIS** | **Point-in-polygon workplace containment verification** |
| Student 6 | Admin Dashboard | React / Web Analytics | Attendance reporting and real-time personnel map |

---

## 3. System Architecture & Workflow

```
[Student 1: Mobile App]
       |
       |  (lat, lon, worker_id, photo)
       v
[Student 2: Backend API Gateway]
       |
       +-----------------------------------+
       |                                   |
       | (worker_id, photo)                | (worker_id, lat, lon, expected_loc)
       v                                   v
[Student 4: AI Face]               [Student 5: GPS + GIS (THIS MODULE)]
       |                                   |
       | YuNet + SFace                     | 1. Validate Coordinates
       | Cosine Sim >= 0.75                | 2. Query TNGIS Inside Boundary
       v                                   | 3. Resolve District/Taluk/Village
   AI: VERIFIED                            v
       |                              GIS: VERIFIED
       |                                   |
       +-----------------+-----------------+
                         |
                         v
       [Student 2: Dual Verification Rule]
          AI == VERIFIED  AND  GIS == VERIFIED ?
                         |
           +-------------+-------------+
           | YES                       | NO
           v                           v
     [ATTENDANCE ACCEPTED]       [ATTENDANCE REJECTED]
```

---

## 4. TNGIS Services Implemented

The dedicated client layer (`app/tngis_client.py`) encapsulates all 10 official TNGIS spatial and administrative services:

| # | TNGIS Service | HTTP Method | Endpoint | Description |
|---|---|---|---|---|
| 1 | **Administrative Data – District** | `GET` | `/administrative/districts` | Fetches Tamil Nadu district list and administrative codes |
| 2 | **Administrative Data – Taluk** | `GET` | `/administrative/taluks` | Fetches taluk administrative records under a district |
| 3 | **Administrative Data – Revenue Village** | `GET` | `/administrative/villages` | Resolves revenue villages under a taluk |
| 4 | **District Spatial Extent** | `GET` | `/extent/district/{id}` | District bounding box for regional pre-filtering |
| 5 | **Taluk Spatial Extent** | `GET` | `/extent/taluk/{id}` | Taluk-level bounding box coordinates |
| 6 | **Revenue Village Spatial Extent** | `GET` | `/extent/village/{id}` | Revenue village cadastral extent box |
| 7 | **Attributes – GIS** | `GET` | `/features/attributes` | Queries cadastral attributes for a given lat/lon |
| 8 | **Multi Feature Attributes – Buffer** | `POST` | `/features/buffer-attributes` | Radius buffer query for surrounding infrastructure |
| 9 | **Nearest Feature** | `POST` | `/spatial/nearest-feature` | Identifies nearest campus gate, checkpoint, or landmark |
| 10 | **Inside Boundary** | `POST` | `/spatial/inside-boundary` | **Core Attendance Check**: Point-in-polygon containment test |

---

## 5. API Configuration & Environment Variables

All gateway configurations and sensitive credentials reside in `.env` (which is excluded from Git via `.gitignore`).

### Environment Template (`.env.example`):
```ini
# TNGIS Base Gateway URL
TNGIS_BASE_URL=https://tngis.tn.gov.in/api/v1

# Application identifier provided by TNeGA / TNGIS authority
TNGIS_APP_NAME=SmartAttendanceERP

# TNGIS API Authentication Token or Key
TNGIS_API_KEY=your_tngis_api_key_here

# Network HTTP Timeout in seconds
TNGIS_TIMEOUT_SECONDS=10.0

# SSL Certificate Verification
TNGIS_VERIFY_SSL=True

# Microservice Server Port
MODULE5_PORT=5005
MODULE5_HOST=0.0.0.0
DEBUG=False
```

---

## 6. Project Folder Structure

```
module5_gis/
│
├── app/
│   ├── __init__.py                 # Flask app factory and public exports
│   ├── config.py                   # Central settings and environment loader
│   ├── tngis_client.py             # HTTP client implementing all 10 TNGIS endpoints
│   ├── boundary_service.py         # Boundary containment resolution & attribute mapping
│   ├── location_service.py         # Coordinate validation & verification pipeline
│   └── routes.py                   # Flask Blueprint (POST /api/location/verify)
│
├── tests/
│   ├── __init__.py
│   ├── test_location_service.py    # Validation & boundary decision unit tests
│   ├── test_boundary_service.py    # GIS point-in-polygon unit tests
│   ├── test_tngis_client.py        # Mocked HTTP tests for all 10 TNGIS services
│   ├── test_routes.py              # Flask endpoint integration tests
│   └── test_live_tngis.py          # Real live gateway network integration probe
│
├── verify_location.py              # Public CLI entry point & Python integration hook
├── demo.py                         # Standalone interactive demonstration
├── app.py                          # Flask microservice server runner
├── pytest.ini                      # Pytest markers and path configuration
├── requirements.txt                # Exact Python dependencies
├── .env.example                    # Sample environment template
├── .gitignore                      # Git exclusion rules
└── README.md                       # Comprehensive documentation
```

---

## 7. Installation & Setup

### Prerequisites
* Python 3.10+ (tested on Python 3.14)
* pip package manager

### Steps
1. Navigate to the module directory:
   ```bash
   cd module5_gis
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   copy .env.example .env
   ```
   *(Edit `.env` to supply your TNGIS API key if connecting to a live TNeGA gateway)*.

---

## 8. Running the Module

### 1. Command-Line Interface (CLI)
Verify any worker coordinates directly from your terminal:
```bash
python verify_location.py W001 12.9249 80.1000 --district Chennai --taluk Tambaram --village Tambaram
```

#### Output (Boundary Inside):
```
=======================================================
 MODULE 5 — GIS LOCATION VERIFICATION
=======================================================
Worker ID       : W001
Latitude        : 12.9249
Longitude       : 80.1
District        : Chengalpattu
Taluk           : Tambaram
Village         : Tambaram
Boundary        : INSIDE
Location Status : VERIFIED
API Status      : SUCCESS
Latency         : 48.2 ms
=======================================================
```

### 2. Standalone Interactive Demo
Run the multi-scenario demonstration script:
```bash
python demo.py
```
This tests:
1. Live TNGIS network probe
2. Worker inside workplace boundary (`VERIFIED`)
3. Worker outside workplace boundary (`REJECTED`)
4. Invalid coordinate rejection (`VALIDATION_ERROR`)
5. Live TNGIS gateway error handling (`API_ERROR` — strictly without faking success)

### 3. Flask REST Microservice
Run the standalone HTTP service on port 5005:
```bash
python app.py
```

---

## 9. Running Automated Tests

Run the full automated test suite (48 tests covering validation, client calls, boundaries, and routes):
```bash
python -m pytest tests/ -v
```

All 47 unit/contract tests execute offline with zero external dependencies using standard mocked responses.

---

## 10. Live TNGIS API Integration Test

The test suite includes a dedicated live gateway test in `tests/test_live_tngis.py`:
```bash
python -m pytest tests/test_live_tngis.py -v -s
```

* **Security & Honesty Guarantee**: If the live TNGIS endpoint is unreachable (e.g. requires state intranet, whitelisted VPN, or active API key), the test **strictly reports the actual connection status** and skips gracefully or asserts `API_ERROR`. **It NEVER falsely converts an unreachable API into `VERIFIED`.**

---

## 11. Standardized API Contracts & Examples

### HTTP Endpoint
`POST /api/location/verify`

### Request Body:
```json
{
  "worker_id": "W001",
  "latitude": 12.9249,
  "longitude": 80.1000,
  "expected_location": {
    "boundary_id": "BND_TAMBARAM_HQ",
    "boundary_layer": "workplace_boundary",
    "district": "Chengalpattu",
    "taluk": "Tambaram",
    "village": "Tambaram"
  }
}
```

---

### Response Types

#### 1. Success (Worker Inside Permitted Boundary) — HTTP 200
```json
{
  "success": true,
  "worker_id": "W001",
  "latitude": 12.9249,
  "longitude": 80.1000,
  "location_verified": true,
  "status": "VERIFIED",
  "boundary_check": "INSIDE",
  "district": "Chengalpattu",
  "taluk": "Tambaram",
  "village": "Tambaram",
  "boundary_id": "BND_TAMBARAM_HQ",
  "api_status": "SUCCESS",
  "latency_ms": 48.2,
  "message": "Worker is inside the permitted boundary."
}
```

#### 2. Rejection (Worker Outside Boundary) — HTTP 200
```json
{
  "success": false,
  "worker_id": "W002",
  "latitude": 13.0499,
  "longitude": 80.2824,
  "location_verified": false,
  "status": "REJECTED",
  "boundary_check": "OUTSIDE",
  "district": "Chennai",
  "taluk": "Mylapore",
  "village": "Triplicane",
  "boundary_id": "BND_TAMBARAM_HQ",
  "api_status": "SUCCESS",
  "latency_ms": 52.1,
  "message": "Worker is outside the permitted boundary."
}
```

#### 3. Gateway Failure / Timeout — HTTP 502 / 504
```json
{
  "success": false,
  "worker_id": "W001",
  "latitude": 12.9249,
  "longitude": 80.1000,
  "location_verified": false,
  "status": "API_ERROR",
  "boundary_check": "UNKNOWN",
  "api_status": "CONNECTION_FAILED",
  "error_type": "TNGISConnectionError",
  "message": "Could not connect to TNGIS API at https://tngis.tn.gov.in/api/v1. Network or server unreachable."
}
```

#### 4. Coordinate Validation Failure — HTTP 400
```json
{
  "success": false,
  "worker_id": "W001",
  "latitude": 195.4000,
  "longitude": 80.1000,
  "location_verified": false,
  "status": "VALIDATION_ERROR",
  "boundary_check": "INVALID",
  "message": "Latitude 195.4 out of range. Must be between -90.0 and 90.0."
}
```

---

## 12. Integration Contract with Student 2 (Backend API)

**Student 2** (FastAPI or Flask Backend) can import and execute verification in Python with a single function call, without needing to know any internal TNGIS endpoints, headers, or JSON payloads:

```python
# ==============================================================================
# STUDENT 2 INTEGRATION HOOK (FASTAPI / FLASK BACKEND)
# ==============================================================================
from module5_gis.verify_location import verify_location

@app.post("/api/v1/attendance/verify-location")
def verify_worker_location(worker_id: str, latitude: float, longitude: float):
    # Retrieve assigned workplace boundary for worker from Student 3's DB
    expected_location = {
        "boundary_id": "BND_CHENNAI_HQ",
        "boundary_layer": "workplace_boundary",
        "district": "Chennai",
        "taluk": "Egmore",
        "village": "Egmore"
    }

    # Execute Module 5 GIS Verification
    gis_result = verify_location(
        worker_id=worker_id,
        latitude=latitude,
        longitude=longitude,
        expected_location=expected_location
    )

    if gis_result["status"] == "VERIFIED":
        return {"status": "SUCCESS", "message": "Location verified."}
    elif gis_result["status"] == "REJECTED":
        return {"status": "FAILED", "reason": "Worker is outside assigned work site."}
    else:
        return {"status": "ERROR", "reason": gis_result["message"]}
```

---

## 13. Dual-Factor Authentication Flow with Student 4 (AI Face)

In final integration, Student 2 combines **Student 4's AI Face Verification** and **Student 5's GIS Location Verification**:

```python
from verify_worker import verify_worker       # Student 4 Module
from verify_location import verify_location   # Student 5 Module (THIS MODULE)

def process_attendance(worker_id, face_image_path, lat, lon, expected_location):
    # Step 1: Biometric Verification
    ai_result = verify_worker(worker_id=worker_id, image_path=face_image_path)
    
    # Step 2: Spatial GIS Verification
    gis_result = verify_location(
        worker_id=worker_id,
        latitude=lat,
        longitude=lon,
        expected_location=expected_location
    )

    # Step 3: Dual Acceptance Rule
    if ai_result.get("verified") and gis_result.get("location_verified"):
        return {
            "attendance": "ACCEPTED",
            "ai_status": ai_result["status"],
            "gis_status": gis_result["status"],
            "similarity": ai_result["similarity"],
            "boundary": gis_result["boundary_check"]
        }
    else:
        return {
            "attendance": "REJECTED",
            "ai_status": ai_result.get("status"),
            "gis_status": gis_result.get("status"),
            "reason": "Both biometric match and workplace GIS boundary containment are required."
        }
```

---

## 14. Real TNGIS API Data vs Local Test Data

To guarantee integrity and avoid false representations:

* **Real TNGIS API Mode**:
  - Activated by pointing `TNGIS_BASE_URL` to an active state gateway and setting `TNGIS_API_KEY`.
  - Dispatches real HTTP requests over the network with millisecond timing.
  - If the live gateway is unreachable or responds with HTTP errors, it returns `status: API_ERROR` and prints `>>> TNGIS API CONNECTION FAILED <<<`.

* **Local Test Data Mode**:
  - Implemented inside `tests/` using `unittest.mock`.
  - Simulates valid and invalid boundary responses for continuous integration without relying on external network availability.
  - Clearly separated from live tests.

---

## 15. System Limitations & Security Notes

1. **GPS Spoofing**: Standard mobile GPS coordinates can theoretically be spoofed via mock location apps on rooted devices. Student 1's mobile app should enforce hardware-level `is_mock_location` checks.
2. **Multipath & Indoor Degradation**: GPS accuracy degrades inside heavy concrete structures ($\pm 15$–$30$ meters). Workplace boundaries in TNGIS should be configured with an appropriate spatial buffer (using `Multi Feature Attributes – Based on Buffer`).
3. **No Secret Leaks**: Logging is strictly configured to mask secrets and tokens. Never log request authorization headers.
4. **Resilience**: The system enforces connection timeouts (default: 10s) to prevent thread exhaustion when external government networks experience latency.

# SecuGen Hamster Pro 20 Local Attendance System

This project is a local biometric attendance system built with Flask, React, SQLite, and the SecuGen FDx SDK.

The React frontend never talks to the scanner directly. It only talks to Flask. Flask can use:

- a local SDK helper built on top of `FDx_SDK_Pro_Windows_v4.3.1_J1.21`
- or the SecuGen WebAPI as a fallback

The SDK helper is now the default and recommended path.

## Folder Structure

```text
Secugen-Hamster/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── requirements.txt
│   └── services/
│       ├── __init__.py
│       ├── fingerprint_service.py
│       ├── sdk_helper_client.py
│       └── webapi_client.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── main.jsx
│       └── styles.css
├── scanner-helper/
│   ├── Program.cs
│   └── SecuGen.ScannerCli.csproj
├── NuGet.Config
└── README.md
```

## Step-By-Step Architecture

### Step 1: Enrollment

1. Open the Registration page.
2. Enter user ID and name.
3. Click `Scan Fingerprint`.
4. React calls Flask `POST /capture`.
5. Flask calls the SecuGen WebAPI capture endpoint.
6. Flask returns the fingerprint template to React.
7. React sends `id`, `name`, and `fingerprintTemplate` to Flask `POST /enroll`.
8. Flask stores the user and template in SQLite.

### Step 2: Authentication and Attendance

1. Open the Attendance page.
2. Select a user.
3. Click `Scan and Verify`.
4. React requests a fresh template from Flask `POST /capture`.
5. React sends the new template and selected user ID to Flask `POST /verify`.
6. Flask performs 1:1 matching against the stored template.
7. If the match succeeds, attendance is saved with a timestamp.
8. If the match fails, the UI shows an error message.

### Step 3: Attendance Records

- Attendance records are stored in SQLite.
- `GET /attendance` returns both the log list and a summary dashboard.
- The Records page shows the saved entries.
- Users can also be deleted from the Registration page, which removes their attendance history too.

## Backend Endpoints

- `GET /health`
- `POST /capture`
- `POST /enroll`
- `POST /verify`
- `GET /attendance`
- `POST /attendance`
- `GET /users`
- `GET /users/<user_id>`
- `DELETE /users/<user_id>`

## Database Schema

### Users Table

- `id TEXT PRIMARY KEY`
- `name TEXT NOT NULL`
- `fingerprint_template TEXT NOT NULL`
- `created_at TEXT NOT NULL`

### Attendance Table

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `user_id TEXT NOT NULL`
- `timestamp TEXT NOT NULL`

## SDK Integration

The folder `FDx_SDK_Pro_Windows_v4.3.1_J1.21` includes local Windows and .NET SDK samples that support:

- device enumeration
- `GetImage`
- `CreateTemplate`
- `MatchTemplate`
- `GetMatchingScore`

This project now integrates that SDK through a small helper CLI:

- `scanner-helper/Program.cs`

Flask runs the helper locally and receives JSON back. This keeps the backend in Python while using the vendor SDK where it is strongest.

## Fingerprint Matching

The code uses a `ScannerClient` abstraction in `backend/services/webapi_client.py`.

### Primary path: local SDK helper

- Capture: helper command `capture`
- Match: helper command `match`
- Helper output: JSON
- Matching decision: score compared against a configurable threshold

### Secondary path: WebAPI fallback

- Capture default: `POST https://localhost:8443/SGIFPCapture`
- Match default: `POST https://localhost:8443/SGIMatchScore`
- Payload type: `application/x-www-form-urlencoded`
- Capture template field: `TemplateBase64`
- Match result field: `MatchingScore`

Important note:

- The SDK helper was built from the local FDx SDK sample capabilities:
  - `FDx SDK Pro for Windows v4.3.1/DotNET/Samples/C#/Matching/mainform.cs`
  - `FDx SDK Pro for Windows v4.3.1/DotNET/Samples/C#/MatchingUAIR/mainform.cs`
- The WebAPI fallback defaults were aligned to the sample included in your zip:
  - `_secugen_zip/WebAPI-Python/app.py`
  - `_secugen_zip/WebAPI-Python/templates/SimpleScan.html`
  - `_secugen_zip/WebAPI-Python/templates/compare.html`
- The SDK path is more reliable because it talks to the scanner directly instead of depending on the local HTTPS service.

## Duplicate Fingerprint Prevention

During enrollment, the backend checks the new template against existing templates before saving the user.

- If a matching fingerprint is found, enrollment is rejected.
- This is a bonus safeguard to prevent double enrollment.

## Mock Fallback

If the WebAPI is not available and `ENABLE_MOCK_SCANNER=true`, the backend uses a deterministic mock fallback.

### What that means

- Capture returns a predictable mock template based on the user ID.
- Verification uses template equality in mock mode.
- This is useful for frontend and workflow testing when the physical scanner or WebAPI is offline.

This fallback is for development and testing only.

## Setup Instructions

### Prerequisites

Install locally:

- Python 3.10 or newer
- Node.js 18 or newer
- npm 9 or newer
- SecuGen Hamster Pro 20 drivers
- SecuGen WebAPI configured and running locally

### 1. Build the local SDK helper

```powershell
cd C:\Users\bhuvi\Dev\Secugen-Hamster
$env:DOTNET_CLI_HOME="C:\Users\bhuvi\Dev\Secugen-Hamster\.dotnet-home"
$env:APPDATA="C:\Users\bhuvi\Dev\Secugen-Hamster\.appdata"
$env:NUGET_PACKAGES="C:\Users\bhuvi\Dev\Secugen-Hamster\.nuget-packages"
dotnet build scanner-helper\SecuGen.ScannerCli.csproj -c Debug --configfile C:\Users\bhuvi\Dev\Secugen-Hamster\NuGet.Config
```

You can check scanner visibility with:

```powershell
C:\Users\bhuvi\Dev\Secugen-Hamster\scanner-helper\bin\Debug\net8.0-windows\SecuGen.ScannerCli.exe health
```

### 2. Optional: run the WebAPI fallback

If you still want the older HTTPS path available, ensure the local SecuGen service is available at:

- `https://localhost:8443`

This is now optional, not required for the main path.

### 2. Start the Flask backend

```powershell
cd C:\Users\bhuvi\Dev\Secugen-Hamster\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Backend URL:

- `http://127.0.0.1:5000`

### 3. Start the React frontend

```powershell
cd C:\Users\bhuvi\Dev\Secugen-Hamster\frontend
npm install
npm run dev
```

Frontend URL:

- `http://127.0.0.1:5173`

## Optional Environment Variables

```powershell
$env:WEBAPI_BASE_URL="https://localhost:8443"
$env:WEBAPI_CAPTURE_ENDPOINT="/SGIFPCapture"
$env:WEBAPI_MATCH_ENDPOINT="/SGIMatchScore"
$env:WEBAPI_TIMEOUT="12"
$env:WEBAPI_VERIFY_SSL="false"
$env:WEBAPI_MATCH_THRESHOLD="100"
$env:WEBAPI_LICENSE=""
$env:SCANNER_BACKEND="sdk"
$env:SDK_HELPER_PATH="C:\Users\bhuvi\Dev\Secugen-Hamster\scanner-helper\bin\Debug\net8.0-windows\SecuGen.ScannerCli.exe"
$env:SDK_CAPTURE_TIMEOUT_MS="10000"
$env:SDK_MIN_QUALITY="50"
$env:SDK_SECURITY_LEVEL="3"
$env:SDK_MATCH_THRESHOLD="100"
$env:ENABLE_MOCK_SCANNER="true"
```

## Important Files

- `backend/app.py`: Flask API routes
- `backend/database.py`: SQLite schema and queries
- `backend/services/sdk_helper_client.py`: local FDx SDK helper integration
- `backend/services/webapi_client.py`: scanner and WebAPI integration
- `backend/services/fingerprint_service.py`: enrollment, verification, duplicate checks, attendance
- `scanner-helper/Program.cs`: C# CLI built on the SecuGen FDx SDK
- `frontend/src/App.jsx`: main UI
- `frontend/src/api.js`: frontend-to-backend API wrapper

## Error Handling

The system handles these cases gracefully:

- Scanner unavailable
- WebAPI request failures
- SecuGen `ErrorCode` responses
- Missing required fields
- Unknown user IDs
- Fingerprint mismatch
- Duplicate user IDs
- Duplicate fingerprint enrollment

## Debugging Tips

- Check Flask logs when capture or verification fails.
- Use `GET /health` to confirm backend configuration.
- Keep mock mode enabled until your real capture and match endpoints are confirmed.
- If capture works but matching does not, inspect the actual WebAPI match response and update the parser in `webapi_client.py`.

## Beginner-Friendly Improvements

- Add filtering by date on the Records page
- Add export to CSV
- Add admin login
- Replace mock matching with your exact SecuGen SDK validation flow if your local WebAPI does not expose a match endpoint

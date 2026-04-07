from flask import Flask, jsonify, request
from flask_cors import CORS

from config import Config
from database import (
    delete_user,
    fetch_attendance,
    fetch_attendance_summary,
    fetch_user,
    fetch_users,
    init_db,
)
from services.fingerprint_service import FingerprintService
from services.sdk_helper_client import SdkHelperClient
from services.webapi_client import ScannerClient, ScannerUnavailableError


app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

init_db(app.config["DATABASE_PATH"])

if app.config["SCANNER_BACKEND"] == "sdk":
    scanner_client = SdkHelperClient(
        helper_path=app.config["SDK_HELPER_PATH"],
        timeout_ms=app.config["SDK_CAPTURE_TIMEOUT_MS"],
        min_quality=app.config["SDK_MIN_QUALITY"],
        security_level=app.config["SDK_SECURITY_LEVEL"],
        match_threshold=app.config["SDK_MATCH_THRESHOLD"],
    )
else:
    scanner_client = ScannerClient(
        base_url=app.config["WEBAPI_BASE_URL"],
        capture_endpoint=app.config["WEBAPI_CAPTURE_ENDPOINT"],
        match_endpoint=app.config["WEBAPI_MATCH_ENDPOINT"],
        timeout=app.config["WEBAPI_TIMEOUT"],
        enable_mock=app.config["ENABLE_MOCK_SCANNER"],
        license_string=app.config["WEBAPI_LICENSE"],
        verify_ssl=app.config["WEBAPI_VERIFY_SSL"],
        match_threshold=app.config["WEBAPI_MATCH_THRESHOLD"],
    )
fingerprint_service = FingerprintService(app.config["DATABASE_PATH"], scanner_client)


@app.get("/health")
def health_check():
    match_threshold = (
        app.config["SDK_MATCH_THRESHOLD"]
        if app.config["SCANNER_BACKEND"] == "sdk"
        else app.config["WEBAPI_MATCH_THRESHOLD"]
    )
    return jsonify(
        {
            "status": "ok",
            "scannerBackend": app.config["SCANNER_BACKEND"],
            "mockScannerEnabled": app.config["ENABLE_MOCK_SCANNER"],
            "webApiBaseUrl": app.config["WEBAPI_BASE_URL"],
            "matchThreshold": match_threshold,
            "verifySsl": app.config["WEBAPI_VERIFY_SSL"],
            "sdkHelperPath": app.config["SDK_HELPER_PATH"],
        }
    )


@app.post("/capture")
def capture():
    payload = request.get_json(silent=True) or {}
    user_identifier = payload.get("userId") or payload.get("name")

    try:
        # Capture returns a template for matching plus a preview image for the UI.
        capture_result = fingerprint_service.capture_template(user_identifier=user_identifier)
        return jsonify(
            {
                "success": True,
                "template": capture_result["template"],
                "image": capture_result["image"],
                "scannerSource": capture_result["source"],
                "scannerResponse": capture_result["raw_response"],
            }
        )
    except ScannerUnavailableError as exc:
        return jsonify({"success": False, "message": f"Scanner unavailable: {exc}"}), 503


@app.post("/enroll")
def enroll():
    payload = request.get_json(silent=True) or {}
    user_id = str(payload.get("id", "")).strip()
    name = str(payload.get("name", "")).strip()
    fingerprint_template = payload.get("fingerprintTemplate")

    if not user_id or not name or not fingerprint_template:
        return jsonify({"success": False, "message": "ID, name, and fingerprint template are required."}), 400

    try:
        user = fingerprint_service.enroll_user(user_id, name, fingerprint_template)
        return jsonify({"success": True, "user": user}), 201
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 409
    except ScannerUnavailableError as exc:
        return jsonify({"success": False, "message": f"Fingerprint check failed: {exc}"}), 503


@app.post("/verify")
def verify():
    payload = request.get_json(silent=True) or {}
    user_id = str(payload.get("id", "")).strip()
    fingerprint_template = payload.get("fingerprintTemplate")

    if not user_id or not fingerprint_template:
        return jsonify({"success": False, "message": "ID and fingerprint template are required."}), 400

    try:
        verification = fingerprint_service.verify_and_mark_attendance(user_id, fingerprint_template)
        if not verification["matched"]:
            return jsonify(
                {
                    "success": False,
                    "message": f"Fingerprint verification failed. Score {verification['score']} is below threshold {verification['threshold']}.",
                    "user": verification["user"],
                    "score": verification["score"],
                    "threshold": verification["threshold"],
                    "scannerSource": verification["scanner_source"],
                    "scannerResponse": verification["scanner_response"],
                }
            ), 401

        return jsonify(
            {
                "success": True,
                "message": "Attendance marked successfully.",
                "attendance": {
                    "id": verification["attendance_id"],
                    "timestamp": verification["timestamp"],
                },
                "score": verification["score"],
                "threshold": verification["threshold"],
                "user": verification["user"],
                "scannerSource": verification["scanner_source"],
                "scannerResponse": verification["scanner_response"],
            }
        )
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404
    except ScannerUnavailableError as exc:
        return jsonify({"success": False, "message": f"Verification failed: {exc}"}), 503


@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if request.method == "GET":
        return jsonify(
            {
                "success": True,
                "records": fetch_attendance(app.config["DATABASE_PATH"]),
                "summary": fetch_attendance_summary(app.config["DATABASE_PATH"]),
            }
        )

    payload = request.get_json(silent=True) or {}
    user_id = str(payload.get("user_id", "")).strip()
    timestamp = payload.get("timestamp")

    if not user_id:
        return jsonify({"success": False, "message": "user_id is required."}), 400

    try:
        attendance_record = fingerprint_service.log_attendance(user_id, timestamp=timestamp)
        return jsonify({"success": True, "attendance": attendance_record}), 201
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404


@app.get("/users")
def list_users():
    return jsonify({"success": True, "users": fetch_users(app.config["DATABASE_PATH"])})


@app.get("/users/<user_id>")
def get_user(user_id):
    user = fetch_user(app.config["DATABASE_PATH"], user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    return jsonify(
        {
            "success": True,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "created_at": user["created_at"],
            },
        }
    )


@app.delete("/users/<user_id>")
def remove_user(user_id):
    deleted_user = delete_user(app.config["DATABASE_PATH"], user_id)
    if not deleted_user:
        return jsonify({"success": False, "message": "User not found."}), 404

    return jsonify(
        {
            "success": True,
            "message": f"Deleted user {deleted_user['name']} ({deleted_user['id']}) and related attendance records.",
            "user": deleted_user,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)

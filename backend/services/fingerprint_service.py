from datetime import datetime

from database import fetch_all_templates, fetch_user, insert_attendance, insert_user


class FingerprintService:
    def __init__(self, database_path, scanner_client):
        self.database_path = database_path
        self.scanner_client = scanner_client

    def capture_template(self, user_identifier=None):
        return self.scanner_client.capture(user_identifier=user_identifier)

    def enroll_user(self, user_id, name, fingerprint_template):
        existing_user = fetch_user(self.database_path, user_id)
        if existing_user:
            raise ValueError(f"User ID '{user_id}' already exists.")

        # Bonus safeguard: reject a second enrollment if the same finger is already stored.
        duplicate = self.find_duplicate_template(fingerprint_template)
        if duplicate:
            raise ValueError(
                f"Fingerprint already appears to belong to user '{duplicate['name']}' ({duplicate['id']})."
            )

        insert_user(self.database_path, user_id, name, fingerprint_template)
        return {"id": user_id, "name": name}

    def verify_and_mark_attendance(self, user_id, probe_template):
        user = fetch_user(self.database_path, user_id)
        if not user:
            raise ValueError("User not found.")

        match_result = self.scanner_client.match(probe_template, user["fingerprint_template"])
        if not match_result["matched"]:
            return {
                "matched": False,
                "score": match_result["score"],
                "threshold": match_result["threshold"],
                "user": {"id": user["id"], "name": user["name"]},
                "scanner_source": match_result["source"],
                "scanner_response": match_result["raw_response"],
            }

        timestamp = datetime.now().isoformat(timespec="seconds")
        # Attendance is only written after a successful 1:1 fingerprint match.
        attendance_id = insert_attendance(self.database_path, user_id, timestamp)
        return {
            "matched": True,
            "attendance_id": attendance_id,
            "timestamp": timestamp,
            "score": match_result["score"],
            "threshold": match_result["threshold"],
            "user": {"id": user["id"], "name": user["name"]},
            "scanner_source": match_result["source"],
            "scanner_response": match_result["raw_response"],
        }

    def log_attendance(self, user_id, timestamp=None):
        user = fetch_user(self.database_path, user_id)
        if not user:
            raise ValueError("User not found.")

        log_timestamp = timestamp or datetime.now().isoformat(timespec="seconds")
        attendance_id = insert_attendance(self.database_path, user_id, log_timestamp)
        return {
            "attendance_id": attendance_id,
            "timestamp": log_timestamp,
            "user": {"id": user["id"], "name": user["name"]},
        }

    def find_duplicate_template(self, fingerprint_template):
        for user in fetch_all_templates(self.database_path):
            match_result = self.scanner_client.match(fingerprint_template, user["fingerprint_template"])
            if match_result["matched"]:
                return user
        return None

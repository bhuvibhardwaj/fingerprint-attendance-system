import json
import subprocess
from pathlib import Path

from services.webapi_client import ScannerUnavailableError


class SdkHelperClient:
    def __init__(self, helper_path, timeout_ms, min_quality, security_level, match_threshold):
        self.helper_path = Path(helper_path)
        self.timeout_ms = timeout_ms
        self.min_quality = min_quality
        self.security_level = security_level
        self.match_threshold = match_threshold

    def capture(self, user_identifier=None):
        payload = self._run(
            [
                "capture",
                "--timeout",
                str(self.timeout_ms),
                "--quality",
                str(self.min_quality),
            ]
        )
        return {
            "template": payload["template"],
            "image": payload.get("image"),
            "source": "sdk",
            "raw_response": payload,
        }

    def match(self, probe_template, reference_template):
        payload = self._run(
            [
                "match",
                "--template1",
                probe_template,
                "--template2",
                reference_template,
                "--security-level",
                str(self.security_level),
            ]
        )
        score = int(payload["score"])
        return {
            "matched": score >= self.match_threshold,
            "score": score,
            "threshold": self.match_threshold,
            "source": "sdk",
            "raw_response": payload,
        }

    def _run(self, args):
        if not self.helper_path.exists():
            raise ScannerUnavailableError(f"SDK helper not found: {self.helper_path}")

        completed = subprocess.run(
            [str(self.helper_path), *args],
            capture_output=True,
            text=True,
            timeout=max(10, int(self.timeout_ms / 1000) + 10),
            check=False,
        )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()

        if not stdout:
            raise ScannerUnavailableError(stderr or "SDK helper returned no output.")

        try:
            payload = json.loads(self._extract_json(stdout))
        except json.JSONDecodeError as exc:
            raise ScannerUnavailableError(f"Invalid SDK helper response: {stdout}") from exc

        if completed.returncode != 0 or not payload.get("success"):
            raise ScannerUnavailableError(payload.get("message") or stderr or "SDK helper failed.")

        if stderr:
            payload["sdkLogs"] = stderr

        return payload

    @staticmethod
    def _extract_json(output):
        start = output.find("{")
        end = output.rfind("}")
        if start == -1 or end == -1 or end < start:
            return output
        return output[start : end + 1]

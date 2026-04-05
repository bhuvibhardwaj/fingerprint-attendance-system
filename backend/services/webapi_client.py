import hashlib
from datetime import datetime

import requests
import urllib3


class ScannerUnavailableError(Exception):
    pass


class ScannerClient:
    def __init__(
        self,
        base_url,
        capture_endpoint,
        match_endpoint,
        timeout,
        enable_mock,
        license_string="",
        verify_ssl=False,
        match_threshold=100,
    ):
        self.base_url = base_url.rstrip("/")
        self.capture_endpoint = capture_endpoint
        self.match_endpoint = match_endpoint
        self.timeout = timeout
        self.enable_mock = enable_mock
        self.license_string = license_string
        self.verify_ssl = verify_ssl
        self.match_threshold = match_threshold

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def capture(self, user_identifier=None):
        payload = {
            "timeout": str(self.timeout * 1000),
            "quality": "50",
            "licstr": self.license_string,
            "templateformat": "ISO",
            "imagewsqrate": "0.75",
            "fakeDetection": "0",
        }

        try:
            # The browser never reaches the scanner directly. All scanner access stays on the backend.
            response = requests.post(
                f"{self.base_url}{self.capture_endpoint}",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
            data = response.json()
            self._raise_if_error_code(data)
            template = self._extract_template(data)
            return {
                "template": template,
                "image": data.get("BMPBase64"),
                "source": "scanner",
                "raw_response": data,
            }
        except (requests.RequestException, ValueError, KeyError) as exc:
            if not self.enable_mock:
                raise ScannerUnavailableError(str(exc)) from exc

            # Deterministic mock templates make local demo flows repeatable when hardware is offline.
            seed = str(user_identifier or "guest")
            mock_template = hashlib.sha256(seed.encode("utf-8")).hexdigest()
            return {
                "template": mock_template,
                "image": None,
                "source": "mock",
                "raw_response": {
                    "message": "WebAPI unavailable, returning deterministic mock template.",
                    "generatedAt": datetime.utcnow().isoformat(),
                },
            }

    def match(self, probe_template, reference_template):
        payload = {
            "licstr": self.license_string,
            "Template1": probe_template,
            "Template2": reference_template,
            "TemplateFormat": "ISO",
        }

        try:
            # Keep matching behind one adapter so the exact SecuGen endpoint can be swapped easily.
            response = requests.post(
                f"{self.base_url}{self.match_endpoint}",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
            data = response.json()
            self._raise_if_error_code(data)
            score = self._extract_match_score(data)
            is_match = score >= self.match_threshold
            return {
                "matched": is_match,
                "score": score,
                "threshold": self.match_threshold,
                "source": "scanner",
                "raw_response": data,
            }
        except (requests.RequestException, ValueError, KeyError) as exc:
            if not self.enable_mock:
                raise ScannerUnavailableError(str(exc)) from exc
            return {
                "matched": probe_template == reference_template,
                "score": self.match_threshold if probe_template == reference_template else 0,
                "threshold": self.match_threshold,
                "source": "mock",
                "raw_response": {
                    "message": "WebAPI match unavailable, using mock equality comparison.",
                    "reason": str(exc),
                },
            }

    @staticmethod
    def _extract_template(payload):
        if "TemplateBase64" in payload and payload["TemplateBase64"]:
            return payload["TemplateBase64"]
        if "template" in payload and payload["template"]:
            return payload["template"]
        if "Template" in payload and payload["Template"]:
            return payload["Template"]
        if "data" in payload and isinstance(payload["data"], dict):
            nested = payload["data"]
            if "template" in nested and nested["template"]:
                return nested["template"]
        raise KeyError("Fingerprint template not found in WebAPI response.")

    @staticmethod
    def _extract_match_score(payload):
        if "MatchingScore" in payload:
            return int(payload["MatchingScore"])
        if "matchingScore" in payload:
            return int(payload["matchingScore"])
        raise KeyError("Matching score not found in WebAPI response.")

    @staticmethod
    def _raise_if_error_code(payload):
        error_code = int(payload.get("ErrorCode", 0))
        if error_code > 0:
            raise ScannerUnavailableError(f"SecuGen WebAPI error code {error_code}")

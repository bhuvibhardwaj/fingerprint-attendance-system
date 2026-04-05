from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "attendance.db"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DATABASE_PATH))
    SCANNER_BACKEND = os.getenv("SCANNER_BACKEND", "sdk")
    SDK_HELPER_PATH = os.getenv(
        "SDK_HELPER_PATH",
        str(BASE_DIR.parent / "scanner-helper" / "bin" / "Debug" / "net8.0-windows" / "SecuGen.ScannerCli.exe"),
    )
    SDK_CAPTURE_TIMEOUT_MS = int(os.getenv("SDK_CAPTURE_TIMEOUT_MS", "10000"))
    SDK_MIN_QUALITY = int(os.getenv("SDK_MIN_QUALITY", "50"))
    SDK_SECURITY_LEVEL = int(os.getenv("SDK_SECURITY_LEVEL", "3"))
    SDK_MATCH_THRESHOLD = int(os.getenv("SDK_MATCH_THRESHOLD", "100"))
    WEBAPI_BASE_URL = os.getenv("WEBAPI_BASE_URL", "https://localhost:8443")
    WEBAPI_CAPTURE_ENDPOINT = os.getenv("WEBAPI_CAPTURE_ENDPOINT", "/SGIFPCapture")
    WEBAPI_MATCH_ENDPOINT = os.getenv("WEBAPI_MATCH_ENDPOINT", "/SGIMatchScore")
    WEBAPI_TIMEOUT = int(os.getenv("WEBAPI_TIMEOUT", "12"))
    WEBAPI_LICENSE = os.getenv("WEBAPI_LICENSE", "")
    WEBAPI_VERIFY_SSL = os.getenv("WEBAPI_VERIFY_SSL", "false").lower() == "true"
    WEBAPI_MATCH_THRESHOLD = int(os.getenv("WEBAPI_MATCH_THRESHOLD", "100"))
    ENABLE_MOCK_SCANNER = os.getenv("ENABLE_MOCK_SCANNER", "true").lower() == "true"

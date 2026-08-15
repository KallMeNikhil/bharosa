import re
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PGP|PRIVATE|ENCRYPTED PRIVATE) KEY-----"),
    re.compile(r"(?i)password\s*=\s*['\"][^'\"\s]{8,}['\"]"),
    re.compile(r"(?i)secret_key\s*=\s*['\"][^'\"\s]{8,}['\"]"),
]

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOT = REPO_ROOT / "backend" / "app"
ALLOWED_SUFFIXES = {".py"}

KEY_FILE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
KEY_FILE_IGNORE_DIRS = {"node_modules", ".git", ".venv", "venv"}


def test_no_hardcoded_secrets_in_app_source():
    offenders = []
    for path in SCAN_ROOT.rglob("*"):
        if path.suffix not in ALLOWED_SUFFIXES or not path.is_file():
            continue
        content = path.read_text(errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                offenders.append((str(path), pattern.pattern))
    assert not offenders, f"Possible hardcoded secrets found: {offenders}"


def test_no_key_material_files_in_repository():
    offenders = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in KEY_FILE_SUFFIXES:
            continue
        if any(part in KEY_FILE_IGNORE_DIRS for part in path.parts):
            continue
        offenders.append(str(path))
    assert not offenders, f"Key material files found in repository: {offenders}"

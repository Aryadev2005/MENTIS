"""Hardware fingerprint generation and license validation."""

import hashlib
import hmac
import json
import logging
import platform
import subprocess
import time
from enum import Enum

from ..config import settings

logger = logging.getLogger(__name__)


class LicenseStatus(str, Enum):
    valid = "valid"
    expired = "expired"
    invalid = "invalid"
    hardware_mismatch = "hardware_mismatch"
    revoked = "revoked"


def _get_mac_fingerprint() -> str:
    """Collect stable hardware identifiers on macOS."""
    components = []

    try:
        result = subprocess.run(
            ["system_profiler", "SPHardwareDataType", "-json"],
            capture_output=True, text=True, timeout=5,
        )
        data = json.loads(result.stdout)
        hw = data.get("SPHardwareDataType", [{}])[0]
        components.append(hw.get("serial_number", ""))
        components.append(hw.get("platform_UUID", ""))
        components.append(hw.get("machine_model", ""))
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["ioreg", "-l", "-d", "2", "-k", "IOPlatformSerialNumber"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "IOPlatformSerialNumber" in line:
                serial = line.split('"')[-2]
                components.append(serial)
                break
    except Exception:
        pass

    components.append(platform.node())
    components.append(platform.machine())

    return hashlib.sha256("|".join(components).encode()).hexdigest()


def _get_windows_fingerprint() -> str:
    """Collect stable hardware identifiers on Windows."""
    components = []

    try:
        result = subprocess.run(
            ["wmic", "csproduct", "get", "UUID", "/value"],
            capture_output=True, text=True, timeout=5,
        )
        uuid_line = [l for l in result.stdout.splitlines() if "UUID=" in l]
        if uuid_line:
            components.append(uuid_line[0].split("=")[1].strip())
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["wmic", "bios", "get", "SerialNumber", "/value"],
            capture_output=True, text=True, timeout=5,
        )
        serial_line = [l for l in result.stdout.splitlines() if "SerialNumber=" in l]
        if serial_line:
            components.append(serial_line[0].split("=")[1].strip())
    except Exception:
        pass

    components.append(platform.node())
    return hashlib.sha256("|".join(components).encode()).hexdigest()


def get_hardware_fingerprint() -> str:
    """Return a stable SHA-256 hardware fingerprint for the current machine."""
    system = platform.system()
    try:
        if system == "Darwin":
            return _get_mac_fingerprint()
        elif system == "Windows":
            return _get_windows_fingerprint()
        else:
            fallback = f"{platform.node()}|{platform.machine()}|{platform.processor()}"
            return hashlib.sha256(fallback.encode()).hexdigest()
    except Exception as e:
        logger.error("Fingerprint generation failed: %s", e)
        return hashlib.sha256(platform.node().encode()).hexdigest()


def generate_license_token(user_id: str, plan: str, fingerprint: str, expires_at: int) -> str:
    """Generate an HMAC-signed license token."""
    payload = f"{user_id}|{plan}|{fingerprint}|{expires_at}"
    sig = hmac.new(
        settings.ENCRYPTION_KEY.encode()[:32],
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}|{sig}"


def validate_license_token(token: str, current_fingerprint: str) -> LicenseStatus:
    """Validate a license token against the current hardware."""
    try:
        parts = token.split("|")
        if len(parts) != 5:
            return LicenseStatus.invalid

        user_id, plan, stored_fingerprint, expires_at_str, stored_sig = parts
        expires_at = int(expires_at_str)

        payload = f"{user_id}|{plan}|{stored_fingerprint}|{expires_at}"
        expected_sig = hmac.new(
            settings.ENCRYPTION_KEY.encode()[:32],
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, stored_sig):
            return LicenseStatus.invalid

        if time.time() > expires_at:
            return LicenseStatus.expired

        if not hmac.compare_digest(stored_fingerprint, current_fingerprint):
            return LicenseStatus.hardware_mismatch

        return LicenseStatus.valid

    except Exception as e:
        logger.error("License validation error: %s", e)
        return LicenseStatus.invalid

"""Utility helpers shared across the Ex Healthcare backend."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ex_healthcare import __version__ as app_version

_BASE_DIR = Path(__file__).resolve().parent
_VERSION_FILE = _BASE_DIR / "public" / "ex_healthcare_suite" / "version.json"
_FALLBACK_VERSION: str | None = None


def _read_version_file() -> str | None:
	"""
	Read version from version.json file.

	Returns:
		str | None: Version string or None if file doesn't exist or is invalid
	"""
	if not _VERSION_FILE.exists():
		return None

	try:
		data = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
	except (json.JSONDecodeError, OSError, ValueError):
		return None

	version = data.get("version") or data.get("buildVersion")
	return str(version) if version else None


def get_build_version() -> str:
	"""
	Return a string that uniquely identifies the current asset build.

	Tries version.json first (generated during a frontend build, if
	ex_healthcare has one), falls back to app version + timestamp if missing.

	Returns:
		str: Unique build version identifier
	"""
	version = _read_version_file()
	if version:
		return version

	global _FALLBACK_VERSION
	if _FALLBACK_VERSION is None:
		_FALLBACK_VERSION = f"{app_version}-{int(time.time())}"
	return _FALLBACK_VERSION


def get_app_version() -> str:
	"""Get the application version from __init__.py"""
	return app_version

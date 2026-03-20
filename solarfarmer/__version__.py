"""Dynamic version information from package metadata and git.

This module provides version information with the following fallback chain:
- __version__: Package metadata → pyproject.toml → "unknown"
- __released__: Most recent git tag date → "unreleased" (development)
"""

__all__ = ["__version__", "__released__"]


def _get_version():
    """Get version from package metadata, fallback to pyproject.toml for development.

    Returns:
        str: Version string (e.g., "0.1.0") or "unknown" if unavailable.
    """
    # First try: installed package metadata (pip install)
    try:
        from importlib.metadata import version

        return version("solarfarmer")
    except Exception:
        pass

    # Second try: development mode - read from pyproject.toml
    try:
        from pathlib import Path

        pyproject_path = Path(__file__).parents[1] / "pyproject.toml"

        # Try Python 3.11+ tomllib first
        try:
            import tomllib

            with pyproject_path.open("rb") as f:
                data = tomllib.load(f)
            return data["project"]["version"]
        except ImportError:
            # Fallback for Python 3.10: simple regex parsing
            import re

            with pyproject_path.open(encoding="utf-8") as f:
                content = f.read()
            match = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if match:
                return match.group(1)
    except Exception:
        pass

    return "unknown"


def _get_release_date():
    """Get release date from most recent git tag.

    Returns:
        str: ISO date string (YYYY-MM-DD) of last tagged release,
             or "unreleased" if no tags exist (development mode).
    """
    import subprocess

    try:
        # Get the date of the most recent tag
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", "--tags", "--no-walk"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
            cwd=None,  # Use current directory
        )

        if result.returncode == 0 and result.stdout.strip():
            # Parse git date format: "2026-02-23 10:30:45 +0100"
            date_str = result.stdout.strip().split()[0]
            return date_str
    except Exception:
        pass

    # If no tags exist, this is unreleased development version
    return "unreleased"


__version__ = _get_version()
__released__ = _get_release_date()

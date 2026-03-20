import re

from solarfarmer.__version__ import __released__, __version__


class TestVersion:
    def test_version_format(self):
        """Version matches X.Y.Z semver or falls back to 'unknown'."""
        assert re.match(r"^\d+\.\d+\.\d+", __version__) or __version__ == "unknown"


class TestReleasedDate:
    def test_released_format(self):
        """Released is either an ISO date (YYYY-MM-DD) or 'unreleased'."""
        assert __released__ == "unreleased" or re.match(r"^\d{4}-\d{2}-\d{2}$", __released__)

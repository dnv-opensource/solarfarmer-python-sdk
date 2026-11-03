import re

from solarfarmer.__version__ import __released__, __version__


class TestVersion:
    def test_version_format(self):
        """Version matches X.Y.Z semver or falls back to 'unknown'."""
        assert re.match(r"^\d+\.\d+\.\d+", __version__) or __version__ == "unknown"


class TestTopLevelExports:
    def test_version_and_released_exposed_on_package(self):
        """Both attributes are reachable as ``solarfarmer.<attr>``, not only via the submodule."""
        import solarfarmer as sf

        assert sf.__version__ == __version__
        assert sf.__released__ == __released__


class TestReleasedDate:
    def test_released_format(self):
        """Released is either an ISO date (YYYY-MM-DD) or 'unreleased'."""
        assert __released__ == "unreleased" or re.match(r"^\d{4}-\d{2}-\d{2}$", __released__)

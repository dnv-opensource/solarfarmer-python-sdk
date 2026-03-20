import os
from pathlib import Path

import pytest


@pytest.fixture
def api_key():
    """Get API key from environment variable."""
    key = os.getenv("SF_API_KEY")
    if not key:
        pytest.skip("SF_API_KEY environment variable not set")
    return key


@pytest.fixture
def sample_data_dir():
    """Return path to sample data directory."""
    return Path(__file__).parent.parent / "docs" / "notebooks" / "sample_data"


@pytest.fixture
def bern_2d_racks_inputs():
    """Return path to Bern 2D racks sample input folder."""
    path = (
        Path(__file__).parent.parent / "docs" / "notebooks" / "sample_data" / "Inputs_Bern_2D_racks"
    )
    assert path.exists(), f"Sample data path does not exist: {path}"
    return str(path)

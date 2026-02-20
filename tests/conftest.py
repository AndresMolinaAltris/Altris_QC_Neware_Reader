import sys
import pytest
from pathlib import Path

# Add project root to path so all project modules are importable from tests/
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

NDAX_DIR = PROJECT_ROOT / "test_ndax_files"


@pytest.fixture(scope="session")
def sample_ndax_path():
    """Return path to the first .ndax file in the test directory."""
    files = sorted(NDAX_DIR.glob("*.ndax"))
    if not files:
        pytest.skip("No .ndax files found in test_ndax_files/")
    return str(files[0])


@pytest.fixture(scope="session")
def loaded_df(sample_ndax_path):
    """Load the sample NDAX file and return the DataFrame."""
    from NewareNDA.NewareNDAx import read_ndax
    return read_ndax(sample_ndax_path, software_cycle_number=True)


@pytest.fixture
def data_loader(sample_ndax_path):
    """Create a DataLoader, load the sample file, yield it, then clear on teardown."""
    from data_loader import DataLoader
    loader = DataLoader()
    loader.load_files([sample_ndax_path])
    yield loader
    loader.clear_cache()

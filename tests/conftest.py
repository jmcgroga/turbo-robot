"""
Pytest configuration and shared fixtures.
"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture(scope="session")
def test_data_path():
    """Get the path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def temp_data_dir(test_data_path):
    """Create a temporary directory with test data for each test."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    # Copy test data files to temp directory
    for json_file in test_data_path.glob("*.json"):
        shutil.copy(json_file, temp_path / json_file.name)
    
    yield temp_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


# Configure pytest to ignore matplotlib UserWarnings during tests
@pytest.fixture(autouse=True)
def configure_matplotlib():
    """Configure matplotlib for testing."""
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    
    # Suppress matplotlib warnings during tests
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="matplotlib")


# Set up test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "cli: mark test as CLI test")
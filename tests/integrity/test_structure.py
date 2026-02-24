import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_directory_structure():
    """Verify that all professional directory structures exist."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    required_dirs = [
        "backend",
        "frontend",
        "frontend/views",
        "frontend/components",
        "frontend/core",
        "data",
        "tests"
    ]
    
    for d in required_dirs:
        assert os.path.isdir(os.path.join(base_dir, d)), f"Directory {d} is missing!"

def test_critical_files():
    """Verify that main execution and config files exist."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    required_files = [
        "kuyumcu_pro.py",
        "backend/main.py",
        "backend/models.py",
        "backend/run_server.py",
        "frontend/app.py",
        "frontend/run_client.py"
    ]
    
    for f in required_files:
        assert os.path.isfile(os.path.join(base_dir, f)), f"Critical file {f} is missing!"

def test_backend_imports():
    """Ensure that backend modules can be imported without errors."""
    try:
        from backend import main, models, schemas, database
        assert True
    except ImportError as e:
        pytest.fail(f"Backend import failed: {e}")

def test_frontend_imports():
    """Ensure that frontend modules and views can be imported without errors."""
    try:
        from frontend import app
        from frontend.views import dashboard, boss, settings, analytics
        from frontend.core import config
        assert True
    except ImportError as e:
        pytest.fail(f"Frontend import failed: {e}")

def test_database_path_logic():
    """Ensure the database is pointing to the absolute 'data' directory."""
    from backend.database import DATABASE_URL, DATA_DIR
    assert "data" in DATA_DIR
    assert os.path.isabs(DATA_DIR)
    assert DATABASE_URL.startswith("sqlite")

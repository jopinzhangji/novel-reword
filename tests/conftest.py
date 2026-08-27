# Shared fixtures for tests (project root, paths)
import pytest
from pathlib import Path

# Project root: tests/ -> parent is root
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def project_root():
    return PROJECT_ROOT


@pytest.fixture
def dev_agent_output_dir(project_root):
    return project_root / "dev_agent" / "output"

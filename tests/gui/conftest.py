"""Shared Qt fixtures for GUI tests."""

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Single QApplication instance for the test session."""
    app = QApplication.instance() or QApplication([])
    yield app

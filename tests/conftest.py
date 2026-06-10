"""Shared pytest fixtures (extended in S1+)."""

from __future__ import annotations

import pytest


@pytest.fixture
def project_root(tmp_path):
    """Isolated directory for future session-dir tests."""
    return tmp_path

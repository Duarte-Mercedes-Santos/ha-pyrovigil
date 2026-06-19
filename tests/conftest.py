"""Shared test fixtures for Pyrovigil."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.loader import DATA_CUSTOM_COMPONENTS

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def enable_custom_integrations(hass: HomeAssistant) -> None:
    """Enable custom integrations defined in the test dir."""
    hass.data.pop(DATA_CUSTOM_COMPONENTS)


@pytest.fixture
def anepc_response_data() -> dict:
    """Load sample ANEPC ArcGIS response."""
    return json.loads((FIXTURES_DIR / "anepc_response.json").read_text())


@pytest.fixture
def anepc_empty_data() -> dict:
    """Load empty ANEPC response."""
    return json.loads((FIXTURES_DIR / "anepc_empty.json").read_text())


@pytest.fixture
def rcm_d0_data() -> dict:
    """Load sample RCM d0 response."""
    return json.loads((FIXTURES_DIR / "rcm_d0.json").read_text())


@pytest.fixture
def warnings_data() -> list[dict]:
    """Load sample IPMA warnings response."""
    return json.loads((FIXTURES_DIR / "warnings.json").read_text())

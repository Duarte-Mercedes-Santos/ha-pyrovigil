"""Tests for Pyrovigil API client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.pyrovigil.api import PyrovigilApiClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock aiohttp ClientSession."""
    return AsyncMock(spec=aiohttp.ClientSession)


def _mock_response(data: dict | list, status: int = 200) -> AsyncMock:
    """Create a mock aiohttp response."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=data)
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=status,
        )
    # Support async context manager
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


class TestGetNearbyFires:
    """Tests for async_get_nearby_fires."""

    @pytest.mark.asyncio
    async def test_returns_features(self, mock_session: AsyncMock) -> None:
        data = _load_fixture("anepc_response.json")
        mock_session.get.return_value = _mock_response(data)

        client = PyrovigilApiClient(mock_session)
        result = await client.async_get_nearby_fires(38.72, -9.14, 25)

        assert len(result) == 3
        assert result[0]["Numero"] == "20260001234"

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_session: AsyncMock) -> None:
        data = _load_fixture("anepc_empty.json")
        mock_session.get.return_value = _mock_response(data)

        client = PyrovigilApiClient(mock_session)
        result = await client.async_get_nearby_fires(38.72, -9.14, 25)

        assert result == []

    @pytest.mark.asyncio
    async def test_builds_correct_url_params(self, mock_session: AsyncMock) -> None:
        data = _load_fixture("anepc_empty.json")
        mock_session.get.return_value = _mock_response(data)

        client = PyrovigilApiClient(mock_session)
        await client.async_get_nearby_fires(38.72, -9.14, 50)

        mock_session.get.assert_called_once()
        call_kwargs = mock_session.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")

        assert "CodNatureza" in params["where"]
        assert params["geometry"] == "-9.14,38.72"
        assert params["distance"] == "50000"
        assert params["f"] == "json"

    @pytest.mark.asyncio
    async def test_pagination(self, mock_session: AsyncMock) -> None:
        page1 = _load_fixture("anepc_response.json")
        page1["exceededTransferLimit"] = True

        page2 = _load_fixture("anepc_response.json")
        # Change IDs on page2 so they're distinct
        for i, f in enumerate(page2["features"]):
            f["attributes"]["Numero"] = f"page2_{i}"

        mock_session.get.side_effect = [
            _mock_response(page1),
            _mock_response(page2),
        ]

        client = PyrovigilApiClient(mock_session)
        result = await client.async_get_nearby_fires(38.72, -9.14, 25)

        assert len(result) == 6  # 3 from each page
        assert mock_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_http_error_raises(self, mock_session: AsyncMock) -> None:
        mock_session.get.return_value = _mock_response({}, status=500)

        client = PyrovigilApiClient(mock_session)
        with pytest.raises(aiohttp.ClientResponseError):
            await client.async_get_nearby_fires(38.72, -9.14, 25)

    @pytest.mark.asyncio
    async def test_timeout_raises(self, mock_session: AsyncMock) -> None:
        mock_session.get.side_effect = TimeoutError()

        client = PyrovigilApiClient(mock_session)
        with pytest.raises(TimeoutError):
            await client.async_get_nearby_fires(38.72, -9.14, 25)

    @pytest.mark.asyncio
    async def test_pagination_capped(self, mock_session: AsyncMock) -> None:
        """Pagination should stop after ANEPC_MAX_PAGES iterations."""
        page = _load_fixture("anepc_response.json")
        page["exceededTransferLimit"] = True

        mock_session.get.return_value = _mock_response(page)

        client = PyrovigilApiClient(mock_session)
        await client.async_get_nearby_fires(38.72, -9.14, 25)

        # Should stop at max pages (5)
        assert mock_session.get.call_count == 5


class TestGetFireRisk:
    """Tests for async_get_fire_risk."""

    @pytest.mark.asyncio
    async def test_returns_parsed_json(self, mock_session: AsyncMock) -> None:
        data = _load_fixture("rcm_d0.json")
        mock_session.get.return_value = _mock_response(data)

        client = PyrovigilApiClient(mock_session)
        result = await client.async_get_fire_risk(day=0)

        assert result["dataPrev"] == "2026-06-17"
        assert "1106" in result["local"]
        assert result["local"]["1106"]["data"]["rcm"] == 3

    @pytest.mark.asyncio
    async def test_day_parameter_in_url(self, mock_session: AsyncMock) -> None:
        mock_session.get.return_value = _mock_response({"local": {}})

        client = PyrovigilApiClient(mock_session)
        await client.async_get_fire_risk(day=1)

        call_args = mock_session.get.call_args
        url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url", "")
        assert "rcm-d1.json" in str(url)

    @pytest.mark.asyncio
    async def test_http_error_raises(self, mock_session: AsyncMock) -> None:
        mock_session.get.return_value = _mock_response({}, status=503)

        client = PyrovigilApiClient(mock_session)
        with pytest.raises(aiohttp.ClientResponseError):
            await client.async_get_fire_risk(day=0)


class TestGetWeatherWarnings:
    """Tests for async_get_weather_warnings."""

    @pytest.mark.asyncio
    async def test_returns_warnings_list(self, mock_session: AsyncMock) -> None:
        data = _load_fixture("warnings.json")
        mock_session.get.return_value = _mock_response(data)

        client = PyrovigilApiClient(mock_session)
        result = await client.async_get_weather_warnings()

        assert len(result) == 3
        assert result[0]["awarenessTypeName"] == "Trovoada"

    @pytest.mark.asyncio
    async def test_empty_warnings(self, mock_session: AsyncMock) -> None:
        mock_session.get.return_value = _mock_response([])

        client = PyrovigilApiClient(mock_session)
        result = await client.async_get_weather_warnings()

        assert result == []

    @pytest.mark.asyncio
    async def test_http_error_raises(self, mock_session: AsyncMock) -> None:
        mock_session.get.return_value = _mock_response([], status=500)

        client = PyrovigilApiClient(mock_session)
        with pytest.raises(aiohttp.ClientResponseError):
            await client.async_get_weather_warnings()

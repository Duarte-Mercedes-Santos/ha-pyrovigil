"""API client for Pyrovigil — handles all external HTTP communication."""

from __future__ import annotations

import logging

import aiohttp

from .const import (
    ANEPC_BASE_URL,
    ANEPC_MAX_PAGES,
    ANEPC_OUT_FIELDS,
    ANEPC_PAGE_SIZE,
    AQICN_URL_TEMPLATE,
    EXCLUDED_STATUS_GROUPS,
    FIRE_NATURE_CODES,
    FIRMS_BBOX_DEGREES,
    FIRMS_URL_TEMPLATE,
    FOGOS_ACTIVE_URL,
    IPMA_OBSERVATIONS_URL,
    IPMA_RCM_URL_TEMPLATE,
    IPMA_STATIONS_URL,
    IPMA_WARNINGS_URL,
)

_LOGGER = logging.getLogger(__name__)


class PyrovigilApiClient:
    """API client for ANEPC and IPMA data sources."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_get_nearby_fires(
        self,
        lat: float,
        lon: float,
        radius_km: int,
    ) -> list[dict]:
        """Fetch fire incidents near the given coordinates from ANEPC ArcGIS.

        Returns a list of raw feature attribute dicts.
        """
        nature_filter = ",".join(str(c) for c in sorted(FIRE_NATURE_CODES))
        status_exclusion = ",".join(f"'{s}'" for s in sorted(EXCLUDED_STATUS_GROUPS))
        all_features: list[dict] = []

        for page in range(ANEPC_MAX_PAGES):
            params = {
                "where": (
                    f"CodNatureza IN ({nature_filter})"
                    f" AND EstadoAgrupado NOT IN ({status_exclusion})"
                ),
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "spatialRel": "esriSpatialRelIntersects",
                "distance": str(radius_km * 1000),
                "units": "esriSRUnit_Meter",
                "outFields": ",".join(ANEPC_OUT_FIELDS),
                "resultRecordCount": str(ANEPC_PAGE_SIZE),
                "resultOffset": str(page * ANEPC_PAGE_SIZE),
                "f": "json",
            }

            async with self._session.get(ANEPC_BASE_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

            features = data.get("features", [])
            all_features.extend(f["attributes"] for f in features)

            if not data.get("exceededTransferLimit"):
                break

        return all_features

    async def async_get_fire_risk(self, day: int = 0) -> dict:
        """Fetch IPMA RCM fire risk forecast.

        Args:
            day: 0 for today, 1 for tomorrow, 2 for day after.

        Returns parsed JSON dict.
        """
        url = IPMA_RCM_URL_TEMPLATE.format(day=day)

        async with self._session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def async_get_weather_warnings(self) -> list[dict]:
        """Fetch IPMA weather warnings.

        Returns a list of raw warning dicts.
        """
        async with self._session.get(IPMA_WARNINGS_URL) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def async_get_fogos_active(self) -> list[dict]:
        """Fetch active incidents from fogos.pt with burn area data.

        Returns a list of incident dicts.
        """
        async with self._session.get(FOGOS_ACTIVE_URL) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("data", [])

    async def async_get_firms_hotspots(
        self,
        lat: float,
        lon: float,
        api_key: str,
    ) -> list[dict]:
        """Fetch NASA FIRMS satellite hotspots near coordinates.

        Returns a list of hotspot dicts parsed from CSV.
        """
        bbox_deg = FIRMS_BBOX_DEGREES
        url = FIRMS_URL_TEMPLATE.format(
            api_key=api_key,
            west=round(lon - bbox_deg, 2),
            south=round(lat - bbox_deg, 2),
            east=round(lon + bbox_deg, 2),
            north=round(lat + bbox_deg, 2),
        )

        async with self._session.get(url) as resp:
            resp.raise_for_status()
            text = await resp.text()

        lines = text.strip().split("\n")
        if len(lines) < 2:
            return []

        headers = lines[0].split(",")
        hotspots = []
        for line in lines[1:]:
            values = line.split(",")
            if len(values) >= len(headers):
                hotspots.append(dict(zip(headers, values, strict=False)))
        return hotspots

    async def async_get_weather_observations(self) -> dict:
        """Fetch IPMA weather station observations (includes wind)."""
        async with self._session.get(IPMA_OBSERVATIONS_URL) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def async_get_weather_stations(self) -> list[dict]:
        """Fetch IPMA weather station metadata (coordinates)."""
        async with self._session.get(IPMA_STATIONS_URL) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def async_get_air_quality(self, lat: float, lon: float, token: str) -> dict:
        """Fetch air quality from AQICN for the nearest station."""
        url = AQICN_URL_TEMPLATE.format(lat=lat, lon=lon, token=token)
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

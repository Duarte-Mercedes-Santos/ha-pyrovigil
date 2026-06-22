"""Data update coordinators for Pyrovigil."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PyrovigilApiClient
from .const import EXCLUDED_STATUS_GROUPS, WIND_DIRECTION_DEGREES, WIND_DIRECTION_LABELS
from .mappings import find_nearest_area_aviso, find_nearest_dico, haversine
from .models import (
    AirQualityData,
    AnepcData,
    FireIncident,
    FireRiskData,
    FireRiskEntry,
    FirmsData,
    FirmsHotspot,
    WeatherWarning,
    WeatherWarningData,
    WindData,
)

_LOGGER = logging.getLogger(__name__)

WARNING_LEVEL_PRIORITY = {"green": 0, "yellow": 1, "orange": 2, "red": 3}


class AnepcCoordinator(DataUpdateCoordinator[AnepcData]):
    """Coordinator for ANEPC fire incident data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PyrovigilApiClient,
        lat: float,
        lon: float,
        radius_km: int,
        update_interval: timedelta,
        safety_margin_km: int = 0,
        alert_interval: timedelta | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Pyrovigil ANEPC",
            update_interval=update_interval,
        )
        self._api = api
        self._lat = lat
        self._lon = lon
        self._radius_km = radius_km
        self._safety_margin_km = safety_margin_km
        self._normal_interval = update_interval
        self._alert_interval = alert_interval
        self._known_fire_ids: set[str] = set()
        self._previous_fires: dict[str, FireIncident] = {}
        self._in_alert_mode = False

    async def _async_update_data(self) -> AnepcData:
        try:
            query_radius = self._radius_km + self._safety_margin_km
            raw_fires = await self._api.async_get_nearby_fires(self._lat, self._lon, query_radius)
        except Exception as err:
            raise UpdateFailed(f"Error fetching ANEPC data: {err}") from err

        # Fetch burn area data from fogos.pt (best-effort)
        burn_area_map = await self._fetch_burn_areas()

        fires: list[FireIncident] = []
        for attrs in raw_fires:
            # Skip concluded/closed fires
            status_group = str(attrs.get("EstadoAgrupado", ""))
            if status_group in EXCLUDED_STATUS_GROUPS:
                continue

            lat = float(attrs.get("Latitude", 0))
            lon = float(attrs.get("Longitude", 0))
            dist = haversine(self._lat, self._lon, lat, lon)

            severity = FireIncident.compute_severity(
                int(attrs.get("Operacionais", 0) or 0),
                int(attrs.get("MeiosAereos", 0) or 0),
            )

            fire_id = str(attrs.get("Numero", ""))
            burn_area = burn_area_map.get(fire_id, 0.0)
            adjusted = None
            if burn_area > 0:
                fire_radius = FireIncident.fire_radius_from_area(burn_area)
                adjusted = max(0.0, dist - fire_radius)

            # Escalation tracking vs previous poll
            resource_trend = "stable"
            distance_trend = "stable"
            personnel_change = 0
            prev = self._previous_fires.get(fire_id)
            if prev is not None:
                personnel_now = int(attrs.get("Operacionais", 0) or 0)
                personnel_change = personnel_now - prev.personnel
                if personnel_change > 5:
                    resource_trend = "escalating"
                elif personnel_change < -5:
                    resource_trend = "deescalating"

                prev_eff = prev.effective_distance_km
                curr_eff = adjusted if adjusted is not None else dist
                diff = curr_eff - prev_eff
                if diff < -0.5:
                    distance_trend = "approaching"
                elif diff > 0.5:
                    distance_trend = "receding"

            fires.append(
                FireIncident.from_api_response(
                    attrs,
                    distance_km=dist,
                    severity=severity,
                    burn_area_ha=burn_area,
                    adjusted_distance_km=adjusted,
                    resource_trend=resource_trend,
                    distance_trend=distance_trend,
                    personnel_change=personnel_change,
                )
            )

        fires.sort(key=lambda f: f.effective_distance_km)

        # Detect new fires and fire events
        current_ids = {f.fire_id for f in fires}
        new_ids = current_ids - self._known_fire_ids
        for fire in fires:
            if fire.fire_id in new_ids:
                self.hass.bus.async_fire(
                    "pyrovigil_fire_detected",
                    {
                        "fire_id": fire.fire_id,
                        "distance_km": round(fire.distance_km, 1),
                        "severity": fire.severity,
                        "nature": fire.nature,
                        "concelho": fire.concelho,
                        "latitude": fire.latitude,
                        "longitude": fire.longitude,
                    },
                )
        self._known_fire_ids = current_ids
        self._previous_fires = {f.fire_id: f for f in fires}

        # Adaptive polling: speed up when fires are nearby, slow down when clear
        if self._alert_interval is not None:
            if fires and not self._in_alert_mode:
                self._in_alert_mode = True
                self.update_interval = self._alert_interval
                _LOGGER.info(
                    "Fires detected nearby — polling increased to every %s",
                    self._alert_interval,
                )
            elif not fires and self._in_alert_mode:
                self._in_alert_mode = False
                self.update_interval = self._normal_interval
                _LOGGER.info(
                    "No fires nearby — polling restored to every %s",
                    self._normal_interval,
                )

        return AnepcData(
            fires=fires,
            nearest_fire=fires[0] if fires else None,
            total_personnel=sum(f.personnel for f in fires),
            total_ground_vehicles=sum(f.ground_vehicles for f in fires),
            total_aircraft=sum(f.aircraft for f in fires),
            last_updated=datetime.now(),
        )

    async def _fetch_burn_areas(self) -> dict[str, float]:
        """Fetch burn area data from fogos.pt, keyed by SADO/Numero ID."""
        try:
            incidents = await self._api.async_get_fogos_active()
        except Exception:
            _LOGGER.debug("Could not fetch fogos.pt burn area data")
            return {}

        result: dict[str, float] = {}
        for inc in incidents:
            sado_id = str(inc.get("sadoId", ""))
            fire_id = str(inc.get("id", ""))
            icnf = inc.get("icnf") or {}
            burn = icnf.get("burnArea") or {}
            total = float(burn.get("total", 0) or 0)
            if total > 0:
                if sado_id:
                    result[sado_id] = total
                if fire_id:
                    result[fire_id] = total
        return result


class FireRiskCoordinator(DataUpdateCoordinator[FireRiskData]):
    """Coordinator for IPMA fire risk (RCM) data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PyrovigilApiClient,
        lat: float,
        lon: float,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Pyrovigil Fire Risk",
            update_interval=update_interval,
        )
        self._api = api
        self._lat = lat
        self._lon = lon
        self._dico_code: str | None = None

    async def _async_update_data(self) -> FireRiskData:
        try:
            rcm_d0 = await self._api.async_get_fire_risk(day=0)

            # Resolve DICO code on first run
            if self._dico_code is None:
                self._dico_code = find_nearest_dico(self._lat, self._lon, rcm_d0)
                if self._dico_code is None:
                    _LOGGER.warning(
                        "Could not find DICO code for coordinates (%s, %s)",
                        self._lat,
                        self._lon,
                    )
                    return FireRiskData()

            # Get today's risk
            today_entry = self._extract_risk(rcm_d0, self._dico_code)

            # Get tomorrow's risk
            tomorrow_entry = None
            try:
                rcm_d1 = await self._api.async_get_fire_risk(day=1)
                tomorrow_entry = self._extract_risk(rcm_d1, self._dico_code)
            except Exception:
                _LOGGER.debug("Could not fetch tomorrow's fire risk")

            return FireRiskData(
                today=today_entry,
                tomorrow=tomorrow_entry,
                dico_code=self._dico_code,
                forecast_date=rcm_d0.get("dataPrev", ""),
            )
        except Exception as err:
            raise UpdateFailed(f"Error fetching fire risk data: {err}") from err

    @staticmethod
    def _extract_risk(rcm_data: dict, dico_code: str) -> FireRiskEntry | None:
        local = rcm_data.get("local", {})
        entry = local.get(dico_code)
        if entry is None:
            return None
        return FireRiskEntry(
            dico_code=dico_code,
            rcm=entry.get("data", {}).get("rcm", 0),
            latitude=float(entry.get("latitude", 0)),
            longitude=float(entry.get("longitude", 0)),
        )


class WeatherWarningCoordinator(DataUpdateCoordinator[WeatherWarningData]):
    """Coordinator for IPMA weather warnings."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PyrovigilApiClient,
        lat: float,
        lon: float,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Pyrovigil Weather Warnings",
            update_interval=update_interval,
        )
        self._api = api
        self._lat = lat
        self._lon = lon
        self._area_code: str | None = find_nearest_area_aviso(lat, lon)

    async def _async_update_data(self) -> WeatherWarningData:
        try:
            raw_warnings = await self._api.async_get_weather_warnings()
        except Exception as err:
            raise UpdateFailed(f"Error fetching weather warnings: {err}") from err

        if self._area_code is None:
            return WeatherWarningData()

        warnings = [
            WeatherWarning.from_api_response(w)
            for w in raw_warnings
            if w.get("idAreaAviso") == self._area_code
        ]

        highest = "green"
        for w in warnings:
            level = w.awareness_level
            if WARNING_LEVEL_PRIORITY.get(level, 0) > WARNING_LEVEL_PRIORITY.get(highest, 0):
                highest = level

        return WeatherWarningData(
            warnings=warnings,
            highest_level=highest,
        )


class FirmsCoordinator(DataUpdateCoordinator[FirmsData]):
    """Coordinator for NASA FIRMS satellite hotspot data (optional)."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PyrovigilApiClient,
        lat: float,
        lon: float,
        api_key: str,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Pyrovigil FIRMS",
            update_interval=update_interval,
        )
        self._api = api
        self._lat = lat
        self._lon = lon
        self._api_key = api_key

    async def _async_update_data(self) -> FirmsData:
        try:
            raw_hotspots = await self._api.async_get_firms_hotspots(
                self._lat, self._lon, self._api_key
            )
        except Exception as err:
            raise UpdateFailed(f"Error fetching FIRMS data: {err}") from err

        hotspots: list[FirmsHotspot] = []
        for h in raw_hotspots:
            try:
                lat = float(h.get("latitude", 0))
                lon = float(h.get("longitude", 0))
                dist = haversine(self._lat, self._lon, lat, lon)
                hotspots.append(
                    FirmsHotspot(
                        latitude=lat,
                        longitude=lon,
                        brightness=float(h.get("bright_ti4", 0) or 0),
                        confidence=str(h.get("confidence", "")),
                        frp=float(h.get("frp", 0) or 0),
                        distance_km=dist,
                    )
                )
            except (ValueError, TypeError):
                continue

        hotspots.sort(key=lambda h: h.distance_km)

        return FirmsData(
            hotspots=hotspots,
            nearest_hotspot_km=hotspots[0].distance_km if hotspots else None,
            count=len(hotspots),
        )


class WindCoordinator(DataUpdateCoordinator[WindData]):
    """Coordinator for IPMA wind observations at the nearest station."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PyrovigilApiClient,
        lat: float,
        lon: float,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Pyrovigil Wind",
            update_interval=update_interval,
        )
        self._api = api
        self._lat = lat
        self._lon = lon
        self._nearest_station_id: str | None = None
        self._nearest_station_name: str = ""
        self._nearest_station_dist: float = 0.0

    async def _async_update_data(self) -> WindData:
        try:
            # Resolve nearest station on first run
            if self._nearest_station_id is None:
                stations = await self._api.async_get_weather_stations()
                best_dist = float("inf")
                for s in stations:
                    s_lat = float(s.get("latitude", 0))
                    s_lon = float(s.get("longitude", 0))
                    dist = haversine(self._lat, self._lon, s_lat, s_lon)
                    if dist < best_dist:
                        best_dist = dist
                        self._nearest_station_id = str(
                            s.get("properties", {}).get("idEstacao", s.get("idEstacao", ""))
                        )
                        self._nearest_station_name = str(
                            s.get("properties", {}).get("localEstacao", s.get("localEstacao", ""))
                        )
                        self._nearest_station_dist = dist

            obs = await self._api.async_get_weather_observations()

            # Find the latest observation for our station
            wind_speed = 0.0
            wind_dir_id = -1
            for timestamp in sorted(obs.keys(), reverse=True):
                station_data = obs[timestamp].get(self._nearest_station_id, {})
                speed = station_data.get("intensidadeVentoKM")
                if speed is not None and speed != -99.0:
                    wind_speed = float(speed)
                    wind_dir_id = int(station_data.get("idDireccVento", -1))
                    break

            return WindData(
                speed_kmh=wind_speed,
                direction_id=wind_dir_id,
                direction_label=WIND_DIRECTION_LABELS.get(wind_dir_id, "Unknown"),
                direction_degrees=WIND_DIRECTION_DEGREES.get(wind_dir_id, 0.0),
                station_name=self._nearest_station_name,
                station_distance_km=self._nearest_station_dist,
            )
        except Exception as err:
            raise UpdateFailed(f"Error fetching wind data: {err}") from err


class AirQualityCoordinator(DataUpdateCoordinator[AirQualityData]):
    """Coordinator for AQICN air quality data (optional)."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PyrovigilApiClient,
        lat: float,
        lon: float,
        token: str,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Pyrovigil Air Quality",
            update_interval=update_interval,
        )
        self._api = api
        self._lat = lat
        self._lon = lon
        self._token = token

    async def _async_update_data(self) -> AirQualityData:
        try:
            data = await self._api.async_get_air_quality(self._lat, self._lon, self._token)

            if data.get("status") != "ok":
                return AirQualityData()

            aq = data.get("data", {})
            iaqi = aq.get("iaqi", {})

            return AirQualityData(
                aqi=int(aq.get("aqi", 0)),
                dominant_pollutant=str(aq.get("dominentpol", "")),
                station_name=str(aq.get("city", {}).get("name", "")),
                pm25=float(iaqi["pm25"]["v"]) if "pm25" in iaqi else None,
                pm10=float(iaqi["pm10"]["v"]) if "pm10" in iaqi else None,
            )
        except Exception as err:
            raise UpdateFailed(f"Error fetching air quality data: {err}") from err

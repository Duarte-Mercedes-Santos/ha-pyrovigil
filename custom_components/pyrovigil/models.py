"""Data models for the Pyrovigil integration."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FireIncident:
    """A single fire incident from ANEPC."""

    fire_id: str
    nature_code: int
    nature: str
    status_code: int
    status: str
    status_group: str
    latitude: float
    longitude: float
    distance_km: float
    concelho: str
    freguesia: str
    locality: str
    personnel: int
    ground_personnel: int
    aerial_personnel: int
    ground_vehicles: int
    aircraft: int
    entities_count: int
    started: str
    duration: str
    duration_minutes: int
    severity: str = "low"
    burn_area_ha: float = 0.0
    adjusted_distance_km: float | None = None
    # Escalation tracking (populated by coordinator from previous poll)
    resource_trend: str = "stable"  # "escalating", "deescalating", "stable"
    distance_trend: str = "stable"  # "approaching", "receding", "stable"
    personnel_change: int = 0

    @classmethod
    def from_api_response(
        cls,
        attrs: dict,
        distance_km: float,
        severity: str = "low",
        burn_area_ha: float = 0.0,
        adjusted_distance_km: float | None = None,
        resource_trend: str = "stable",
        distance_trend: str = "stable",
        personnel_change: int = 0,
    ) -> FireIncident:
        """Create a FireIncident from raw ArcGIS feature attributes."""
        return cls(
            fire_id=str(attrs.get("Numero", "")),
            nature_code=int(attrs.get("CodNatureza", 0)),
            nature=str(attrs.get("Natureza", "")),
            status_code=int(attrs.get("CodEstadoOcorrencia", 0)),
            status=str(attrs.get("EstadoOcorrencia", "")),
            status_group=str(attrs.get("EstadoAgrupado", "")),
            latitude=float(attrs.get("Latitude", 0.0)),
            longitude=float(attrs.get("Longitude", 0.0)),
            distance_km=distance_km,
            concelho=str(attrs.get("Concelho", "")),
            freguesia=str(attrs.get("Freguesia", "")),
            locality=str(attrs.get("Localidade", "")),
            personnel=int(attrs.get("Operacionais", 0) or 0),
            ground_personnel=int(attrs.get("OperacionaisTerrestres", 0) or 0),
            aerial_personnel=int(attrs.get("OPAereos", 0) or 0),
            ground_vehicles=int(attrs.get("MeiosTerrestres", 0) or 0),
            aircraft=int(attrs.get("MeiosAereos", 0) or 0),
            entities_count=int(attrs.get("QuantEntidades", 0) or 0),
            started=str(attrs.get("DataInicioOcorrencia", "")),
            duration=str(attrs.get("Duracao", "")),
            duration_minutes=int(attrs.get("DuracaoMinutos", 0) or 0),
            severity=severity,
            burn_area_ha=burn_area_ha,
            adjusted_distance_km=adjusted_distance_km,
            resource_trend=resource_trend,
            distance_trend=distance_trend,
            personnel_change=personnel_change,
        )

    @staticmethod
    def compute_severity(personnel: int, aircraft: int) -> str:
        """Compute fire severity from resource deployment."""
        from .const import (
            SEVERITY_HIGH_MAX_PERSONNEL,
            SEVERITY_LOW_MAX_PERSONNEL,
            SEVERITY_MODERATE_MAX_PERSONNEL,
        )

        if personnel > SEVERITY_HIGH_MAX_PERSONNEL or aircraft >= 4:
            return "extreme"
        if personnel > SEVERITY_MODERATE_MAX_PERSONNEL or aircraft >= 2:
            return "high"
        if personnel > SEVERITY_LOW_MAX_PERSONNEL:
            return "moderate"
        return "low"

    @staticmethod
    def fire_radius_from_area(burn_area_ha: float) -> float:
        """Estimate fire radius in km from burned area in hectares."""
        if burn_area_ha <= 0:
            return 0.0
        area_km2 = burn_area_ha * 0.01
        return math.sqrt(area_km2 / math.pi)

    @property
    def effective_distance_km(self) -> float:
        """Best estimate of distance to the active fire front."""
        if self.adjusted_distance_km is not None:
            return self.adjusted_distance_km
        return self.distance_km

    def to_dict(self) -> dict:
        """Convert to a dict suitable for HA entity attributes."""
        result = {
            "fire_id": self.fire_id,
            "nature": self.nature,
            "status": self.status,
            "distance_km": round(self.distance_km, 1),
            "concelho": self.concelho,
            "freguesia": self.freguesia,
            "locality": self.locality,
            "personnel": self.personnel,
            "ground_vehicles": self.ground_vehicles,
            "aircraft": self.aircraft,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "started": self.started,
            "duration": self.duration,
            "severity": self.severity,
            "resource_trend": self.resource_trend,
            "distance_trend": self.distance_trend,
            "personnel_change": self.personnel_change,
        }
        if self.burn_area_ha > 0:
            result["burn_area_ha"] = round(self.burn_area_ha, 1)
            result["adjusted_distance_km"] = (
                round(self.adjusted_distance_km, 1)
                if self.adjusted_distance_km is not None
                else None
            )
        return result


@dataclass(frozen=True, slots=True)
class FireRiskEntry:
    """Fire risk (RCM) data for a single municipality."""

    dico_code: str
    rcm: int
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class WeatherWarning:
    """An IPMA weather warning."""

    awareness_type: str
    awareness_level: str
    area_code: str
    text: str
    start_time: str
    end_time: str

    @classmethod
    def from_api_response(cls, data: dict) -> WeatherWarning:
        """Create a WeatherWarning from raw IPMA JSON."""
        return cls(
            awareness_type=str(data.get("awarenessTypeName", "")),
            awareness_level=str(data.get("awarenessLevelID", "")),
            area_code=str(data.get("idAreaAviso", "")),
            text=str(data.get("text", "")),
            start_time=str(data.get("startTime", "")),
            end_time=str(data.get("endTime", "")),
        )

    def to_dict(self) -> dict:
        """Convert to a dict suitable for HA entity attributes."""
        return {
            "type": self.awareness_type,
            "level": self.awareness_level,
            "text": self.text,
            "start": self.start_time,
            "end": self.end_time,
        }


@dataclass(slots=True)
class AnepcData:
    """Aggregated data from ANEPC coordinator."""

    fires: list[FireIncident] = field(default_factory=list)
    nearest_fire: FireIncident | None = None
    total_personnel: int = 0
    total_ground_vehicles: int = 0
    total_aircraft: int = 0
    last_updated: datetime | None = None


@dataclass(slots=True)
class FireRiskData:
    """Aggregated fire risk data from IPMA."""

    today: FireRiskEntry | None = None
    tomorrow: FireRiskEntry | None = None
    dico_code: str = ""
    forecast_date: str = ""


@dataclass(slots=True)
class WeatherWarningData:
    """Aggregated weather warning data from IPMA."""

    warnings: list[WeatherWarning] = field(default_factory=list)
    highest_level: str = "green"


@dataclass(frozen=True, slots=True)
class FirmsHotspot:
    """A single NASA FIRMS satellite thermal detection."""

    latitude: float
    longitude: float
    brightness: float
    confidence: str
    frp: float
    distance_km: float


@dataclass(slots=True)
class FirmsData:
    """Aggregated FIRMS hotspot data."""

    hotspots: list[FirmsHotspot] = field(default_factory=list)
    nearest_hotspot_km: float | None = None
    count: int = 0


@dataclass(slots=True)
class WindData:
    """Wind observation from the nearest IPMA station."""

    speed_kmh: float = 0.0
    direction_id: int = -1
    direction_label: str = ""
    direction_degrees: float = 0.0
    station_name: str = ""
    station_distance_km: float = 0.0


@dataclass(slots=True)
class AirQualityData:
    """Air quality data from AQICN."""

    aqi: int | None = None
    dominant_pollutant: str = ""
    station_name: str = ""
    pm25: float | None = None
    pm10: float | None = None

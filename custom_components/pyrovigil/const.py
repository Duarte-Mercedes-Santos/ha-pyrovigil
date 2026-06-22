"""Constants for the Pyrovigil integration."""

from datetime import timedelta

DOMAIN = "pyrovigil"

# --- Defaults ---
DEFAULT_RADIUS_KM = 25
DEFAULT_SCAN_INTERVAL_MINUTES = 5
DEFAULT_HIGH_RISK_THRESHOLD = 4
MIN_SCAN_INTERVAL_MINUTES = 1
MAX_SCAN_INTERVAL_MINUTES = 30
MIN_RADIUS_KM = 5
MAX_RADIUS_KM = 100

FIRE_RISK_UPDATE_INTERVAL = timedelta(minutes=60)
WEATHER_WARNING_UPDATE_INTERVAL = timedelta(minutes=30)

# --- Config keys ---
CONF_RADIUS = "radius"
CONF_SAFETY_MARGIN = "safety_margin"
CONF_HIGH_RISK_THRESHOLD = "high_risk_threshold"
CONF_NASA_FIRMS_KEY = "nasa_firms_key"
CONF_ADAPTIVE_POLLING = "adaptive_polling"
CONF_ALERT_SCAN_INTERVAL = "alert_scan_interval"

DEFAULT_ADAPTIVE_POLLING = True
DEFAULT_ALERT_SCAN_INTERVAL_MINUTES = 2
MIN_ALERT_SCAN_INTERVAL_MINUTES = 1

DEFAULT_SAFETY_MARGIN_KM = 5
MIN_SAFETY_MARGIN_KM = 0
MAX_SAFETY_MARGIN_KM = 20

# --- API URLs ---
ANEPC_BASE_URL = (
    "https://services-eu1.arcgis.com/VlrHb7fn5ewYhX6y/arcgis/rest/services"
    "/OcorrenciasSite/FeatureServer/0/query"
)
IPMA_RCM_URL_TEMPLATE = "https://api.ipma.pt/open-data/forecast/meteorology/rcm/rcm-d{day}.json"
IPMA_WARNINGS_URL = "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json"

# --- ANEPC fire nature codes ---
FIRE_NATURE_CODES = {3101, 3103, 3105, 3107, 3111}

# --- ANEPC status codes to exclude (fire is over) ---
# "Em Conclusão" and "Encerrada" mean the fire is no longer active
EXCLUDED_STATUS_GROUPS = {"Em Conclusão", "Encerrada"}

ANEPC_OUT_FIELDS = [
    "Numero",
    "CodNatureza",
    "Natureza",
    "CodEstadoOcorrencia",
    "EstadoOcorrencia",
    "EstadoAgrupado",
    "Latitude",
    "Longitude",
    "Concelho",
    "Freguesia",
    "Localidade",
    "Operacionais",
    "OperacionaisTerrestres",
    "OPAereos",
    "MeiosTerrestres",
    "MeiosAereos",
    "QuantEntidades",
    "DataInicioOcorrencia",
    "Duracao",
    "DuracaoMinutos",
]

ANEPC_PAGE_SIZE = 200
ANEPC_MAX_PAGES = 5

API_TIMEOUT = 10

# --- Fire risk labels (RCM scale 1-5) ---
RCM_LABELS = {
    1: "Reduzido",
    2: "Moderado",
    3: "Elevado",
    4: "Muito Elevado",
    5: "Máximo",
}

# --- Portugal coordinate bounds (mainland + islands) ---
PORTUGAL_LAT_MIN = 32.0
PORTUGAL_LAT_MAX = 42.2
PORTUGAL_LON_MIN = -31.3
PORTUGAL_LON_MAX = -6.1

# --- Max fires in entity attributes ---
MAX_FIRES_IN_ATTRIBUTES = 25

# --- IPMA weather observations (wind data) ---
IPMA_OBSERVATIONS_URL = (
    "https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json"
)
IPMA_STATIONS_URL = "https://api.ipma.pt/open-data/observation/meteorology/stations/stations.json"

# Wind direction IDs from IPMA (0-8, 9=variable)
WIND_DIRECTION_LABELS = {
    0: "N",
    1: "NE",
    2: "E",
    3: "SE",
    4: "S",
    5: "SW",
    6: "W",
    7: "NW",
    8: "N",
    9: "Variable",
}
WIND_DIRECTION_DEGREES = {
    0: 0,
    1: 45,
    2: 90,
    3: 135,
    4: 180,
    5: 225,
    6: 270,
    7: 315,
    8: 360,
}

# --- AQICN air quality API (optional) ---
CONF_AQICN_TOKEN = "aqicn_token"
AQICN_URL_TEMPLATE = "https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"
AQICN_UPDATE_INTERVAL = timedelta(minutes=30)

# --- Fogos.pt API (supplementary burn area data) ---
FOGOS_ACTIVE_URL = "https://api.fogos.pt/v2/incidents/active"

# --- NASA FIRMS (optional satellite hotspots) ---
FIRMS_URL_TEMPLATE = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    "/{api_key}/VIIRS_SNPP_NRT/{west},{south},{east},{north}/1"
)
FIRMS_UPDATE_INTERVAL = timedelta(minutes=30)
FIRMS_BBOX_DEGREES = 0.5  # ~55km in each direction from home

# --- Severity thresholds ---
SEVERITY_LOW_MAX_PERSONNEL = 25
SEVERITY_MODERATE_MAX_PERSONNEL = 100
SEVERITY_HIGH_MAX_PERSONNEL = 250
# Above HIGH_MAX = extreme

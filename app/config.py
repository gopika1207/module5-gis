"""
Configuration module for Module 5: GPS + GIS Location Verification.
Loads environment variables safely with fallbacks and logging setup.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Base directory for module5_gis
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if available
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Also attempt loading from root if run from workspace root
    load_dotenv()

# TNGIS Gateway Settings
TNGIS_BASE_URL = os.getenv("TNGIS_BASE_URL", "https://tngis.tn.gov.in/api/v1").rstrip("/")
TNGIS_APP_NAME = os.getenv("TNGIS_APP_NAME", "SmartAttendanceERP")
TNGIS_API_KEY = os.getenv("TNGIS_API_KEY", "")
TNGIS_TIMEOUT_SECONDS = float(os.getenv("TNGIS_TIMEOUT_SECONDS", "10.0"))
TNGIS_VERIFY_SSL = os.getenv("TNGIS_VERIFY_SSL", "True").lower() in ("true", "1", "yes")

# Flask Service Settings
MODULE5_HOST = os.getenv("MODULE5_HOST", "0.0.0.0")
MODULE5_PORT = int(os.getenv("MODULE5_PORT", "5005"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Coordinate Validation Constraints (WGS 84)
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0

# Tamil Nadu Approximate Spatial Bounding Box for regional sanity checks
# (Lat: 8.0 deg N to 13.6 deg N, Lon: 76.1 deg E to 80.4 deg E)
TN_BBOX = {
    "min_lat": 8.0,
    "max_lat": 13.6,
    "min_lon": 76.1,
    "max_lon": 80.4,
}


def configure_logging(level=logging.INFO):
    """Sets up standard structured logging without secret leaks."""
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] [Module5_GIS] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("module5_gis")

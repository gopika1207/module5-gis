"""
Module 5: GPS + GIS Location Verification Application Package
"""

from flask import Flask
from app import config
from app.config import configure_logging
from app.tngis_client import (
    TNGISClient,
    TNGISClientError,
    TNGISConnectionError,
    TNGISTimeoutError,
    TNGISResponseError,
)
from app.boundary_service import BoundaryService
from app.location_service import LocationService, verify_location


def create_app():
    """Application factory for Flask GIS microservice."""
    configure_logging()
    app = Flask(__name__)
    app.config["DEBUG"] = config.DEBUG

    from app.routes import location_bp
    app.register_blueprint(location_bp)

    return app


__all__ = [
    "create_app",
    "verify_location",
    "LocationService",
    "BoundaryService",
    "TNGISClient",
    "TNGISClientError",
    "TNGISConnectionError",
    "TNGISTimeoutError",
    "TNGISResponseError",
]

#!/usr/bin/env python
"""
Flask Application Server Runner for Module 5: GPS + GIS Location Verification.
Allows running the microservice as an independent REST API daemon on port 5005.
"""

import sys
from pathlib import Path

# Add module5_gis directory to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app, config

app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print(" STARTING MODULE 5: GPS + GIS LOCATION VERIFICATION SERVICE")
    print(f" Host: {config.MODULE5_HOST} | Port: {config.MODULE5_PORT}")
    print(f" TNGIS Gateway: {config.TNGIS_BASE_URL}")
    print(" Endpoint: POST http://localhost:5005/api/location/verify")
    print("=" * 60)
    app.run(host=config.MODULE5_HOST, port=config.MODULE5_PORT, debug=config.DEBUG)

#!/usr/bin/env python
"""
Worker Location Verification CLI & Public Integration Hook
Student 5: GPS + GIS Location Verification
Project: Smart Attendance and Field Activity Monitoring System

Command-Line Usage:
    python verify_location.py W001 12.9249 80.1000 --district Chennai --taluk Tambaram --village Tambaram
    python verify_location.py --worker-id W001 --lat 12.9249 --lon 80.1000 --boundary-id BND_001

Python Usage (for Student 2 Backend integration):
    from verify_location import verify_location
    result = verify_location("W001", 12.9249, 80.1000, expected_location)
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Ensure module path is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import logging
from app import config
config.configure_logging(level=logging.ERROR)

from app.location_service import verify_location as core_verify_location


def verify_location(
    worker_id: str,
    latitude: Union[float, int, str],
    longitude: Union[float, int, str],
    expected_location: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Public integration function for Student 2 (FastAPI/Flask Backend).
    Accepts worker_id, latitude, longitude, and expected_location dict.
    Hides all TNGIS network calls, endpoints, parameters, and payloads behind this contract.
    Returns clean, JSON-serializable dictionary.
    """
    return core_verify_location(
        worker_id=worker_id,
        latitude=latitude,
        longitude=longitude,
        expected_location=expected_location,
    )


def print_banner(title: str):
    print("=" * 55)
    print(f" {title.upper()}")
    print("=" * 55)


def main():
    parser = argparse.ArgumentParser(
        description="Verify a worker's GPS coordinates against TNGIS workplace boundaries."
    )
    parser.add_argument("worker_id", nargs="?", help="Worker ID (e.g. W001)")
    parser.add_argument("latitude", nargs="?", type=float, help="GPS Latitude (e.g. 12.9249)")
    parser.add_argument("longitude", nargs="?", type=float, help="GPS Longitude (e.g. 80.1000)")
    parser.add_argument("--worker-id", dest="worker_id_opt", help="Worker ID")
    parser.add_argument("--lat", dest="latitude_opt", type=float, help="GPS Latitude")
    parser.add_argument("--lon", dest="longitude_opt", type=float, help="GPS Longitude")
    parser.add_argument("--boundary-id", default="BND_TAMBARAM_01", help="Boundary / Workplace ID")
    parser.add_argument("--layer", default="workplace_boundary", help="GIS Boundary layer name")
    parser.add_argument("--district", default="Chennai", help="Expected District")
    parser.add_argument("--taluk", default="Tambaram", help="Expected Taluk")
    parser.add_argument("--village", default="Tambaram", help="Expected Revenue Village")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format only")

    args = parser.parse_args()

    worker_id = args.worker_id_opt or args.worker_id
    latitude = args.latitude_opt if args.latitude_opt is not None else args.latitude
    longitude = args.longitude_opt if args.longitude_opt is not None else args.longitude

    if not worker_id or latitude is None or longitude is None:
        parser.print_help()
        print("\n[ERROR] Worker ID, Latitude, and Longitude are all required.")
        print("Example: python verify_location.py W001 12.9249 80.1000 --district Chennai")
        sys.exit(1)

    expected_location = {
        "boundary_id": args.boundary_id,
        "boundary_layer": args.layer,
        "district": args.district,
        "taluk": args.taluk,
        "village": args.village,
    }

    result = verify_location(
        worker_id=worker_id,
        latitude=latitude,
        longitude=longitude,
        expected_location=expected_location,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print_banner("Module 5 — GIS Location Verification")
    print(f"Worker ID       : {result.get('worker_id')}")
    print(f"Latitude        : {result.get('latitude')}")
    print(f"Longitude       : {result.get('longitude')}")
    print(f"District        : {result.get('district', 'N/A')}")
    print(f"Taluk           : {result.get('taluk', 'N/A')}")
    print(f"Village         : {result.get('village', 'N/A')}")
    print(f"Boundary        : {result.get('boundary_check', 'UNKNOWN')}")
    print(f"Location Status : {result.get('status')}")
    print(f"API Status      : {result.get('api_status', 'N/A')}")
    if "latency_ms" in result:
        print(f"Latency         : {result.get('latency_ms')} ms")
    if result.get("status") == "API_ERROR":
        print(f"Error Message   : {result.get('message')}")
        print(">>> TNGIS API CONNECTION FAILED <<<")
    elif result.get("status") == "VALIDATION_ERROR":
        print(f"Error Message   : {result.get('message')}")
    print("=" * 55)


if __name__ == "__main__":
    main()

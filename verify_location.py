#!/usr/bin/env python

"""
Worker Location Verification CLI & Public Integration Hook

Student 5:
GPS + GIS Location Verification

Project:
Smart Attendance and Field Activity Monitoring System
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Union

# Ensure module path is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import logging
from app import config

config.configure_logging(level=logging.ERROR)

from app.location_service import verify_location as core_verify_location


# ============================================================
# PUBLIC INTEGRATION FUNCTION
# ============================================================

def verify_location(
    worker_id: str,
    latitude: Union[float, int, str],
    longitude: Union[float, int, str],
    gps_accuracy: Union[float, int, str],
    expected_location: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Public integration function for Student 2 Backend.

    Input:
        worker_id
        latitude
        longitude
        gps_accuracy
        expected_location

    Returns:
        JSON-serializable location verification result.
    """

    return core_verify_location(
        worker_id=worker_id,
        latitude=latitude,
        longitude=longitude,
        gps_accuracy=gps_accuracy,
        expected_location=expected_location,
    )


# ============================================================
# BANNER
# ============================================================

def print_banner(title: str):
    print("=" * 60)
    print(f" {title.upper()}")
    print("=" * 60)


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Verify a worker's GPS coordinates against "
            "the permitted workplace GIS boundary."
        )
    )

    # Positional arguments
    parser.add_argument(
        "worker_id",
        nargs="?",
        help="Worker ID (example: W001)"
    )

    parser.add_argument(
        "latitude",
        nargs="?",
        type=float,
        help="GPS Latitude (example: 12.9249)"
    )

    parser.add_argument(
        "longitude",
        nargs="?",
        type=float,
        help="GPS Longitude (example: 80.1000)"
    )

    # Optional arguments
    parser.add_argument(
        "--worker-id",
        dest="worker_id_opt",
        help="Worker ID"
    )

    parser.add_argument(
        "--lat",
        dest="latitude_opt",
        type=float,
        help="GPS Latitude"
    )

    parser.add_argument(
        "--lon",
        dest="longitude_opt",
        type=float,
        help="GPS Longitude"
    )

    parser.add_argument(
        "--accuracy",
        dest="gps_accuracy",
        type=float,
        default=None,
        help="GPS accuracy in meters (example: 8.5)"
    )

    parser.add_argument(
        "--boundary-id",
        default="BND_TAMBARAM_01",
        help="Boundary / Workplace ID"
    )

    parser.add_argument(
        "--layer",
        default="workplace_boundary",
        help="GIS Boundary layer name"
    )

    parser.add_argument(
        "--district",
        default="Chennai",
        help="Expected District"
    )

    parser.add_argument(
        "--taluk",
        default="Tambaram",
        help="Expected Taluk"
    )

    parser.add_argument(
        "--village",
        default="Tambaram",
        help="Expected Revenue Village"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON only"
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Resolve worker ID
    # --------------------------------------------------------

    worker_id = args.worker_id_opt or args.worker_id

    # --------------------------------------------------------
    # Resolve latitude
    # --------------------------------------------------------

    latitude = (
        args.latitude_opt
        if args.latitude_opt is not None
        else args.latitude
    )

    # --------------------------------------------------------
    # Resolve longitude
    # --------------------------------------------------------

    longitude = (
        args.longitude_opt
        if args.longitude_opt is not None
        else args.longitude
    )

    # --------------------------------------------------------
    # Validate required fields
    # --------------------------------------------------------

    if (
        not worker_id
        or latitude is None
        or longitude is None
        or args.gps_accuracy is None
    ):
        parser.print_help()

        print(
            "\n[ERROR] Worker ID, Latitude, Longitude "
            "and GPS Accuracy are required."
        )

        print(
            "\nExample:"
        )

        print(
            "python verify_location.py "
            "W001 12.9249 80.1000 --accuracy 8.5"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Expected workplace location
    # --------------------------------------------------------

    expected_location = {

        "boundary_id": args.boundary_id,

        "boundary_layer": args.layer,

        "district": args.district,

        "taluk": args.taluk,

        "village": args.village,
    }

    # --------------------------------------------------------
    # Call Module 5 verification service
    # --------------------------------------------------------

    result = verify_location(

        worker_id=worker_id,

        latitude=latitude,

        longitude=longitude,

        gps_accuracy=args.gps_accuracy,

        expected_location=expected_location,
    )

    # --------------------------------------------------------
    # JSON output
    # --------------------------------------------------------

    if args.json:

        print(
            json.dumps(
                result,
                indent=2
            )
        )

        return

    # --------------------------------------------------------
    # Human-readable output
    # --------------------------------------------------------

    print_banner(
        "Module 5 — GIS Location Verification"
    )

    print(
        f"Worker ID       : "
        f"{result.get('worker_id')}"
    )

    print(
        f"Latitude        : "
        f"{result.get('latitude')}"
    )

    print(
        f"Longitude       : "
        f"{result.get('longitude')}"
    )

    print(
        f"GPS Accuracy    : "
        f"{result.get('gps_accuracy')} m"
    )

    print(
        f"District        : "
        f"{result.get('district', 'N/A')}"
    )

    print(
        f"Taluk           : "
        f"{result.get('taluk', 'N/A')}"
    )

    print(
        f"Village         : "
        f"{result.get('village', 'N/A')}"
    )

    print(
        f"Boundary        : "
        f"{result.get('boundary_check', 'UNKNOWN')}"
    )

    print(
        f"Location Status : "
        f"{result.get('status')}"
    )

    print(
        f"API Status      : "
        f"{result.get('api_status', 'N/A')}"
    )

    if "latency_ms" in result:

        print(
            f"Latency         : "
            f"{result.get('latency_ms')} ms"
        )

    if result.get("status") == "API_ERROR":

        print(
            f"Error Message   : "
            f"{result.get('message')}"
        )

        print(
            ">>> TNGIS API CONNECTION FAILED <<<"
        )

    elif result.get("status") == "VALIDATION_ERROR":

        print(
            f"Error Message   : "
            f"{result.get('message')}"
        )

    elif result.get("status") == "REJECTED":

        print(
            ">>> WORKER IS OUTSIDE THE PERMITTED "
            "BOUNDARY <<<"
        )

    elif result.get("status") == "VERIFIED":

        print(
            ">>> WORKER LOCATION VERIFIED <<<"
        )

    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()

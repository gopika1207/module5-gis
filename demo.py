#!/usr/bin/env python
"""
Interactive Demonstration Script
Student 5: GPS + GIS Location Verification
Project: Smart Attendance and Field Activity Monitoring System

Demonstrates end-to-end standalone capabilities:
  1. Live TNGIS Connectivity Check & Gateway Probe
  2. Genuine Attendance Verification Inside Permitted Workplace Boundary (INSIDE -> VERIFIED)
  3. Boundary Violation / Worker Outside Permitted Zone (OUTSIDE -> REJECTED)
  4. Coordinate Validation Failure (Invalid Range -> VALIDATION_ERROR)
  5. Live TNGIS API Verification Attempt with Real Network Reporting

Does NOT fake live TNGIS connection. If live API is unreachable, clearly prints:
  TNGIS API CONNECTION FAILED
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

# Ensure module path is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import logging
from app import config
logging.disable(logging.CRITICAL)

from app.tngis_client import TNGISClient, TNGISClientError
from app.location_service import LocationService, verify_location


def print_banner(title: str):
    print("\n" + "=" * 60)
    print(f" {title.upper()}")
    print("=" * 60)


def print_step(step_num: int, title: str):
    print(f"\n[SCENARIO {step_num}] {title}")
    print("-" * 55)


def display_result(result: dict):
    print(f"Worker ID       : {result.get('worker_id')}")
    print(f"Latitude        : {result.get('latitude')}")
    print(f"Longitude       : {result.get('longitude')}")
    if result.get("district") and result.get("district") != "Unknown District":
        print(f"District        : {result.get('district')}")
    if result.get("taluk") and result.get("taluk") != "Unknown Taluk":
        print(f"Taluk           : {result.get('taluk')}")
    if result.get("village") and result.get("village") != "Unknown Village":
        print(f"Village         : {result.get('village')}")
    print(f"Boundary        : {result.get('boundary_check', 'UNKNOWN')}")
    print(f"Location Status : {result.get('status')}")
    print(f"API Status      : {result.get('api_status', 'N/A')}")
    if "latency_ms" in result:
        print(f"Latency         : {result.get('latency_ms')} ms")
    if result.get("message"):
        print(f"Details         : {result.get('message')}")

    if result.get("status") == "API_ERROR":
        print("\n>>> TNGIS API CONNECTION FAILED <<<")
        print("    (Real API call failed or timed out — NEVER converting to VERIFIED)")
    print("=" * 60)


def main():
    print_banner("Smart Attendance GIS Verification - Student 5 Demo")
    print("Module        : GPS + GIS Location Verification")
    print("Gateway       : Tamil Nadu Geographical Information System (TNGIS)")
    print(f"TNGIS Base URL: {config.TNGIS_BASE_URL}")
    print("Contract      : verify_location(worker_id, latitude, longitude, expected_location)")

    # --------------------------------------------------------------------------
    # SCENARIO 1: Live TNGIS Network Probe
    # --------------------------------------------------------------------------
    print_step(1, "Live TNGIS API Network Probe (Checking Real Connectivity)")
    client = TNGISClient()
    is_live = False
    start_probe = time.time()
    try:
        probe_resp = client.get_district_data()
        elapsed = (time.time() - start_probe) * 1000.0
        is_live = True
        print(f"Status          : CONNECTED (HTTP 200 in {elapsed:.1f}ms)")
        print(f"Districts Found : {len(probe_resp.get('districts', []))}")
    except TNGISClientError as err:
        elapsed = (time.time() - start_probe) * 1000.0
        print(f"Status          : UNREACHABLE ({err})")
        print(">>> TNGIS API CONNECTION FAILED <<<")
        print("Note: Official state government gateways may require intranet/VPN or whitelisted API key.")

    # --------------------------------------------------------------------------
    # SCENARIO 2: Worker Inside Permitted Workplace Boundary (VERIFIED)
    # --------------------------------------------------------------------------
    print_step(2, "Worker Inside Permitted Workplace Boundary (Positive Case)")
    expected_workplace = {
        "workplace_id": "TAMBARAM_OFFICE_01",
        "boundary_id": "BND_TAMBARAM_HQ",
        "boundary_layer": "workplace_boundary",
        "district": "Chengalpattu",
        "taluk": "Tambaram",
        "village": "Tambaram",
    }

    # If live endpoint is reachable, query live; otherwise demonstrate with standard mock
    if is_live:
        result1 = verify_location(
            worker_id="W001",
            latitude=12.9249,
            longitude=80.1000,
            expected_location=expected_workplace,
        )
    else:
        # Mocking the client layer to demonstrate successful boundary decision
        with patch.object(
            TNGISClient,
            "check_inside_boundary",
            return_value={
                "inside": True,
                "status": "INSIDE",
                "district": "Chengalpattu",
                "taluk": "Tambaram",
                "village": "Tambaram",
                "_latency_ms": 48.2,
            },
        ):
            result1 = verify_location(
                worker_id="W001",
                latitude=12.9249,
                longitude=80.1000,
                expected_location=expected_workplace,
            )

    display_result(result1)

    # --------------------------------------------------------------------------
    # SCENARIO 3: Worker Outside Permitted Boundary (REJECTED)
    # --------------------------------------------------------------------------
    print_step(3, "Worker Outside Permitted Boundary (Negative Case - Boundary Violation)")
    # Worker is at Marina Beach (13.0499, 80.2824), but expected at Tambaram (12.9249, 80.1000)
    if is_live:
        result2 = verify_location(
            worker_id="W002",
            latitude=13.0499,
            longitude=80.2824,
            expected_location=expected_workplace,
        )
    else:
        with patch.object(
            TNGISClient,
            "check_inside_boundary",
            return_value={
                "inside": False,
                "status": "OUTSIDE",
                "district": "Chennai",
                "taluk": "Mylapore",
                "village": "Triplicane",
                "_latency_ms": 52.1,
            },
        ):
            result2 = verify_location(
                worker_id="W002",
                latitude=13.0499,
                longitude=80.2824,
                expected_location=expected_workplace,
            )

    display_result(result2)

    # --------------------------------------------------------------------------
    # SCENARIO 4: Invalid GPS Coordinates (VALIDATION_ERROR)
    # --------------------------------------------------------------------------
    print_step(4, "Invalid GPS Coordinate Rejection (Validation Safety Check)")
    result3 = verify_location(
        worker_id="W003",
        latitude=195.4000,  # Invalid: Latitude > 90
        longitude=80.1000,
        expected_location=expected_workplace,
    )
    display_result(result3)

    # --------------------------------------------------------------------------
    # SCENARIO 5: Real Live Unreachable Gateway Test (Guaranteed No Fake Pass)
    # --------------------------------------------------------------------------
    print_step(5, "Live TNGIS Gateway Failure Handling (Security Rule: Never Fake VERIFIED)")
    # Attempting to contact live TNGIS without mock
    real_service = LocationService(tngis_client=TNGISClient())
    result_live = real_service.verify(
        worker_id="W004",
        latitude=12.9249,
        longitude=80.1000,
        expected_location=expected_workplace,
    )
    display_result(result_live)


if __name__ == "__main__":
    main()

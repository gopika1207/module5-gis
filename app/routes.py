"""
Flask Routes / Blueprint for Module 5: GPS + GIS Location Verification.
Exposes REST endpoints for Student 2 (Backend API) to verify worker coordinates.
"""

import logging
from flask import Blueprint, request, jsonify
from app.location_service import verify_location, LocationService
from app.tngis_client import TNGISClient, TNGISClientError

logger = logging.getLogger("module5_gis.routes")

location_bp = Blueprint("location_bp", __name__)


@location_bp.route("/api/location/health", methods=["GET"])
def health_check():
    """Health check endpoint for the GIS microservice."""
    return jsonify({
        "service": "Module 5 — GPS + GIS Location Verification",
        "status": "HEALTHY",
        "version": "1.0.0",
    }), 200


@location_bp.route("/api/location/tngis-status", methods=["GET"])
def tngis_status():
    """Probes connectivity to the external TNGIS service."""
    client = TNGISClient()
    try:
        districts = client.get_district_data()
        return jsonify({
            "tngis_connected": True,
            "status": "ONLINE",
            "message": "Successfully contacted TNGIS gateway.",
            "latency_ms": districts.get("_latency_ms", 0.0),
        }), 200
    except TNGISClientError as err:
        return jsonify({
            "tngis_connected": False,
            "status": "UNREACHABLE",
            "message": f"TNGIS API probe failed: {err}",
        }), 502


@location_bp.route("/api/location/verify", methods=["POST"])
def api_verify_location():
    """
    Primary integration endpoint for Student 2 (Backend / API Gateway).
    Verifies worker GPS coordinates against expected GIS workplace boundaries.

    JSON Request Body:
    {
        "worker_id": "W001",
        "latitude": 12.9249,
        "longitude": 80.1000,
        "expected_location": {
            "boundary_id": "BND_CH_001",
            "boundary_layer": "workplace_boundary",
            "district": "Chennai",
            "taluk": "Tambaram",
            "village": "Tambaram"
        }
    }
    """
    if not request.is_json:
        return jsonify({
            "success": False,
            "location_verified": False,
            "status": "VALIDATION_ERROR",
            "message": "Content-Type must be application/json with a valid JSON body.",
        }), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "location_verified": False,
            "status": "VALIDATION_ERROR",
            "message": "Malformed JSON request body.",
        }), 400

    worker_id = data.get("worker_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    expected_location = data.get("expected_location")

    result = verify_location(
        worker_id=worker_id,
        latitude=latitude,
        longitude=longitude,
        expected_location=expected_location,
    )

    status = result.get("status")

    # Map verification outcomes to appropriate HTTP response codes
    if status == "VALIDATION_ERROR":
        response_payload = {"success": False, **result}
        return jsonify(response_payload), 400

    if status == "API_ERROR":
        api_status = result.get("api_status")
        http_code = 504 if api_status == "TIMEOUT" else 502
        response_payload = {"success": False, **result}
        return jsonify(response_payload), http_code

    if status == "INTERNAL_ERROR":
        response_payload = {"success": False, **result}
        return jsonify(response_payload), 500

    # Business decision: VERIFIED or REJECTED
    is_verified = bool(result.get("location_verified", False))
    response_payload = {
        "success": is_verified,
        **result,
    }
    return jsonify(response_payload), 200

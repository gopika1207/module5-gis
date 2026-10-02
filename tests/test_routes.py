"""
Flask route integration tests for Module 5: GPS + GIS Location Verification.
Tests POST /api/location/verify and GET /api/location/health endpoints.
"""

import pytest
import json
from unittest.mock import patch
from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_check_endpoint(client):
    response = client.get("/api/location/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "HEALTHY"


def test_verify_endpoint_missing_json(client):
    response = client.post("/api/location/verify", data="plain text")
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["status"] == "VALIDATION_ERROR"


def test_verify_endpoint_validation_error(client):
    payload = {
        "worker_id": "W001",
        "latitude": 999.0,  # Invalid latitude
        "longitude": 80.1000,
        "expected_location": {"boundary_id": "BND_001"},
    }
    response = client.post("/api/location/verify", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["status"] == "VALIDATION_ERROR"


def test_verify_endpoint_success_inside(client):
    payload = {
        "worker_id": "W001",
        "latitude": 12.9249,
        "longitude": 80.1000,
        "expected_location": {
            "boundary_id": "BND_TAMBARAM",
            "district": "Chennai",
        },
    }

    mock_result = {
        "worker_id": "W001",
        "latitude": 12.9249,
        "longitude": 80.1000,
        "location_verified": True,
        "status": "VERIFIED",
        "boundary_check": "INSIDE",
        "district": "Chennai",
        "taluk": "Tambaram",
        "village": "Tambaram",
        "api_status": "SUCCESS",
    }

    with patch("app.routes.verify_location", return_value=mock_result):
        response = client.post("/api/location/verify", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["status"] == "VERIFIED"
        assert data["boundary_check"] == "INSIDE"


def test_verify_endpoint_success_outside(client):
    payload = {
        "worker_id": "W002",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "expected_location": {"boundary_id": "BND_TAMBARAM"},
    }

    mock_result = {
        "worker_id": "W002",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "location_verified": False,
        "status": "REJECTED",
        "boundary_check": "OUTSIDE",
        "message": "Worker is outside the permitted boundary.",
        "api_status": "SUCCESS",
    }

    with patch("app.routes.verify_location", return_value=mock_result):
        response = client.post("/api/location/verify", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert data["status"] == "REJECTED"
        assert data["boundary_check"] == "OUTSIDE"


def test_verify_endpoint_api_timeout(client):
    payload = {
        "worker_id": "W001",
        "latitude": 12.9249,
        "longitude": 80.1000,
        "expected_location": {"boundary_id": "BND_TAMBARAM"},
    }

    mock_result = {
        "worker_id": "W001",
        "latitude": 12.9249,
        "longitude": 80.1000,
        "location_verified": False,
        "status": "API_ERROR",
        "api_status": "TIMEOUT",
        "message": "TNGIS API request timed out.",
    }

    with patch("app.routes.verify_location", return_value=mock_result):
        response = client.post("/api/location/verify", json=payload)
        assert response.status_code == 504
        data = response.get_json()
        assert data["success"] is False
        assert data["status"] == "API_ERROR"


def test_verify_endpoint_api_connection_error(client):
    payload = {
        "worker_id": "W001",
        "latitude": 12.9249,
        "longitude": 80.1000,
        "expected_location": {"boundary_id": "BND_TAMBARAM"},
    }

    mock_result = {
        "worker_id": "W001",
        "latitude": 12.9249,
        "longitude": 80.1000,
        "location_verified": False,
        "status": "API_ERROR",
        "api_status": "CONNECTION_FAILED",
        "message": "Could not connect to TNGIS.",
    }

    with patch("app.routes.verify_location", return_value=mock_result):
        response = client.post("/api/location/verify", json=payload)
        assert response.status_code == 502
        data = response.get_json()
        assert data["success"] is False
        assert data["status"] == "API_ERROR"

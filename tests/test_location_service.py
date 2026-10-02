"""
Unit tests for LocationService (Module 5).
Validates GPS coordinate checking, worker identification, boundary outcomes, and error handling.
"""

import pytest
from unittest.mock import MagicMock
from app.location_service import LocationService
from app.tngis_client import (
    TNGISClient,
    TNGISConnectionError,
    TNGISTimeoutError,
    TNGISResponseError,
)
from app.boundary_service import BoundaryService


@pytest.fixture
def mock_boundary_service():
    service = MagicMock(spec=BoundaryService)
    return service


@pytest.fixture
def location_service(mock_boundary_service):
    return LocationService(boundary_service=mock_boundary_service)


@pytest.fixture
def valid_expected_location():
    return {
        "workplace_id": "LOC_CHENNAI_HQ",
        "boundary_id": "BND_001",
        "boundary_layer": "workplace_boundary",
        "district": "Chennai",
        "taluk": "Egmore",
        "village": "Egmore",
    }


# ------------------------------------------------------------------------------
# Test 1 & 8: Valid coordinates & Inside boundary result
# ------------------------------------------------------------------------------
def test_valid_coordinates_inside_boundary(location_service, mock_boundary_service, valid_expected_location):
    mock_boundary_service.verify_boundary.return_value = {
        "inside": True,
        "boundary_check": "INSIDE",
        "boundary_id": "BND_001",
        "layer": "workplace_boundary",
        "district": "Chennai",
        "taluk": "Egmore",
        "village": "Egmore",
        "latency_ms": 12.5,
    }

    result = location_service.verify(
        worker_id="W001",
        latitude=13.0827,
        longitude=80.2707,
        expected_location=valid_expected_location,
    )

    assert result["worker_id"] == "W001"
    assert result["latitude"] == 13.0827
    assert result["longitude"] == 80.2707
    assert result["location_verified"] is True
    assert result["status"] == "VERIFIED"
    assert result["boundary_check"] == "INSIDE"
    assert result["district"] == "Chennai"
    assert result["taluk"] == "Egmore"
    assert result["village"] == "Egmore"
    assert result["api_status"] == "SUCCESS"


# ------------------------------------------------------------------------------
# Test 9: Outside boundary result
# ------------------------------------------------------------------------------
def test_valid_coordinates_outside_boundary(location_service, mock_boundary_service, valid_expected_location):
    mock_boundary_service.verify_boundary.return_value = {
        "inside": False,
        "boundary_check": "OUTSIDE",
        "boundary_id": "BND_001",
        "layer": "workplace_boundary",
        "district": "Chennai",
        "taluk": "Egmore",
        "village": "Egmore",
        "latency_ms": 14.1,
    }

    result = location_service.verify(
        worker_id="W002",
        latitude=12.5000,
        longitude=79.9000,
        expected_location=valid_expected_location,
    )

    assert result["worker_id"] == "W002"
    assert result["location_verified"] is False
    assert result["status"] == "REJECTED"
    assert result["boundary_check"] == "OUTSIDE"
    assert "outside" in result["message"].lower()


# ------------------------------------------------------------------------------
# Test 2: Invalid latitude (out of bounds & non-numeric)
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("bad_lat", [91.0, -90.5, 180.0, "invalid_num"])
def test_invalid_latitude(location_service, valid_expected_location, bad_lat):
    result = location_service.verify(
        worker_id="W001",
        latitude=bad_lat,
        longitude=80.2707,
        expected_location=valid_expected_location,
    )

    assert result["location_verified"] is False
    assert result["status"] == "VALIDATION_ERROR"
    assert result["boundary_check"] == "INVALID"
    assert "latitude" in result["message"].lower()


# ------------------------------------------------------------------------------
# Test 3: Invalid longitude (out of bounds & non-numeric)
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("bad_lon", [181.0, -180.5, 360.0, "not_a_lon"])
def test_invalid_longitude(location_service, valid_expected_location, bad_lon):
    result = location_service.verify(
        worker_id="W001",
        latitude=13.0827,
        longitude=bad_lon,
        expected_location=valid_expected_location,
    )

    assert result["location_verified"] is False
    assert result["status"] == "VALIDATION_ERROR"
    assert result["boundary_check"] == "INVALID"
    assert "longitude" in result["message"].lower()


# ------------------------------------------------------------------------------
# Test 4: Missing worker ID
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("bad_id", ["", None, "   ", 123])
def test_missing_worker_id(location_service, valid_expected_location, bad_id):
    result = location_service.verify(
        worker_id=bad_id if isinstance(bad_id, str) else None,
        latitude=13.0827,
        longitude=80.2707,
        expected_location=valid_expected_location,
    )

    assert result["location_verified"] is False
    assert result["status"] == "VALIDATION_ERROR"
    assert "worker_id" in result["message"].lower()


# ------------------------------------------------------------------------------
# Test: Missing or invalid expected_location
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("bad_exp", [None, {}, "invalid_location_string"])
def test_missing_expected_location(location_service, bad_exp):
    result = location_service.verify(
        worker_id="W001",
        latitude=13.0827,
        longitude=80.2707,
        expected_location=bad_exp,
    )

    assert result["location_verified"] is False
    assert result["status"] == "VALIDATION_ERROR"
    assert "expected_location" in result["message"].lower()


# ------------------------------------------------------------------------------
# Test 6: TNGIS API Timeout
# ------------------------------------------------------------------------------
def test_tngis_api_timeout(location_service, mock_boundary_service, valid_expected_location):
    mock_boundary_service.verify_boundary.side_effect = TNGISTimeoutError(
        "TNGIS API timeout after 10.0 seconds"
    )

    result = location_service.verify(
        worker_id="W001",
        latitude=13.0827,
        longitude=80.2707,
        expected_location=valid_expected_location,
    )

    assert result["location_verified"] is False
    assert result["status"] == "API_ERROR"
    assert result["api_status"] == "TIMEOUT"
    assert "timeout" in result["message"].lower()


# ------------------------------------------------------------------------------
# Test 7: TNGIS Connection Failure
# ------------------------------------------------------------------------------
def test_tngis_connection_failure(location_service, mock_boundary_service, valid_expected_location):
    mock_boundary_service.verify_boundary.side_effect = TNGISConnectionError(
        "Could not connect to TNGIS API. Network unreachable."
    )

    result = location_service.verify(
        worker_id="W001",
        latitude=13.0827,
        longitude=80.2707,
        expected_location=valid_expected_location,
    )

    assert result["location_verified"] is False
    assert result["status"] == "API_ERROR"
    assert result["api_status"] == "CONNECTION_FAILED"
    assert "connection" in result["message"].lower()


# ------------------------------------------------------------------------------
# Test: TNGIS HTTP 500 error
# ------------------------------------------------------------------------------
def test_tngis_http_error(location_service, mock_boundary_service, valid_expected_location):
    mock_boundary_service.verify_boundary.side_effect = TNGISResponseError(
        "TNGIS API returned HTTP 500: Internal Server Error", status_code=500
    )

    result = location_service.verify(
        worker_id="W001",
        latitude=13.0827,
        longitude=80.2707,
        expected_location=valid_expected_location,
    )

    assert result["location_verified"] is False
    assert result["status"] == "API_ERROR"
    assert result["api_status"] == "HTTP_ERROR"
    assert result["http_status_code"] == 500

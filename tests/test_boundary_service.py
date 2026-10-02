"""
Unit tests for BoundaryService (Module 5).
Validates boundary containment evaluation, attribute parsing, and GIS metadata extraction.
"""

import pytest
from unittest.mock import MagicMock
from app.boundary_service import BoundaryService
from app.tngis_client import TNGISClient


@pytest.fixture
def mock_client():
    return MagicMock(spec=TNGISClient)


@pytest.fixture
def boundary_service(mock_client):
    return BoundaryService(client=mock_client)


def test_boundary_check_inside_boolean(boundary_service, mock_client):
    mock_client.check_inside_boundary.return_value = {
        "inside": True,
        "boundary_id": "BND_CHENNAI_01",
        "attributes": {
            "district": "Chennai",
            "taluk": "Guindy",
            "village": "Alandur",
        },
        "_latency_ms": 35.4,
    }

    result = boundary_service.verify_boundary(
        latitude=13.0067,
        longitude=80.2025,
        expected_location={"boundary_id": "BND_CHENNAI_01"},
    )

    assert result["inside"] is True
    assert result["boundary_check"] == "INSIDE"
    assert result["district"] == "Chennai"
    assert result["taluk"] == "Guindy"
    assert result["village"] == "Alandur"
    assert result["latency_ms"] == 35.4


def test_boundary_check_outside_boolean(boundary_service, mock_client):
    mock_client.check_inside_boundary.return_value = {
        "inside": False,
        "boundary_id": "BND_CHENNAI_01",
        "attributes": {},
        "_latency_ms": 28.0,
    }

    result = boundary_service.verify_boundary(
        latitude=12.2000,
        longitude=79.1000,
        expected_location={"boundary_id": "BND_CHENNAI_01"},
    )

    assert result["inside"] is False
    assert result["boundary_check"] == "OUTSIDE"


def test_boundary_check_status_string_inside(boundary_service, mock_client):
    mock_client.check_inside_boundary.return_value = {
        "status": "INSIDE",
        "district": "Madurai",
        "taluk": "Madurai South",
        "village": "Avaniyapuram",
    }

    result = boundary_service.verify_boundary(
        latitude=9.9252,
        longitude=78.1198,
        expected_location={"boundary_id": "BND_MDU_01"},
    )

    assert result["inside"] is True
    assert result["boundary_check"] == "INSIDE"
    assert result["district"] == "Madurai"


def test_boundary_check_status_string_outside(boundary_service, mock_client):
    mock_client.check_inside_boundary.return_value = {
        "status": "OUTSIDE",
    }

    result = boundary_service.verify_boundary(
        latitude=9.5000,
        longitude=77.5000,
        expected_location={"boundary_id": "BND_MDU_01"},
    )

    assert result["inside"] is False
    assert result["boundary_check"] == "OUTSIDE"


def test_boundary_check_features_list(boundary_service, mock_client):
    # GeoJSON / WFS style response
    mock_client.check_inside_boundary.return_value = {
        "features": [{"id": "polygon.1", "properties": {"name": "Tech Park"}}],
    }

    result = boundary_service.verify_boundary(
        latitude=12.9249,
        longitude=80.1000,
        expected_location={"boundary_id": "BND_TECHPARK"},
    )

    assert result["inside"] is True
    assert result["boundary_check"] == "INSIDE"


def test_boundary_check_empty_features_list(boundary_service, mock_client):
    mock_client.check_inside_boundary.return_value = {
        "features": [],
    }

    result = boundary_service.verify_boundary(
        latitude=12.9249,
        longitude=80.1000,
        expected_location={"boundary_id": "BND_TECHPARK"},
    )

    assert result["inside"] is False
    assert result["boundary_check"] == "OUTSIDE"

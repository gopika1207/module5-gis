"""
Unit tests for TNGISClient (Module 5).
Validates all 10 TNGIS HTTP services using mocked session responses.
Tests timeout, connection failure, and HTTP error handling.
"""

import pytest
from unittest.mock import MagicMock, patch
import requests
from app.tngis_client import (
    TNGISClient,
    TNGISClientError,
    TNGISConnectionError,
    TNGISTimeoutError,
    TNGISResponseError,
)


@pytest.fixture
def client():
    return TNGISClient(
        base_url="https://mock-tngis.tn.gov.in/api/v1",
        app_name="TestAttendanceApp",
        api_key="secret-token-123",
        timeout=5.0,
    )


def test_client_headers(client):
    headers = client._build_headers()
    assert headers["X-App-Name"] == "TestAttendanceApp"
    assert headers["Authorization"] == "Bearer secret-token-123"
    assert headers["X-API-Key"] == "secret-token-123"
    assert "SmartAttendance-GISModule" in headers["User-Agent"]


def test_get_district_data(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"districts": [{"id": "D01", "name": "Chennai"}]}

    with patch.object(client.session, "request", return_value=mock_resp) as mock_req:
        res = client.get_district_data(district_name="Chennai")
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        assert kwargs["method"] == "GET"
        assert kwargs["params"] == {"district_name": "Chennai"}
        assert "districts" in res
        assert "_latency_ms" in res


def test_get_taluk_data(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"taluks": [{"id": "T01", "name": "Tambaram"}]}

    with patch.object(client.session, "request", return_value=mock_resp) as mock_req:
        res = client.get_taluk_data(district_code="D01")
        args, kwargs = mock_req.call_args
        assert kwargs["params"] == {"district_code": "D01"}
        assert res["taluks"][0]["name"] == "Tambaram"


def test_get_village_data(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"villages": [{"id": "V01", "name": "Tambaram"}]}

    with patch.object(client.session, "request", return_value=mock_resp) as mock_req:
        res = client.get_village_data(taluk_code="T01")
        args, kwargs = mock_req.call_args
        assert kwargs["params"] == {"taluk_code": "T01"}
        assert len(res["villages"]) == 1


def test_spatial_extents(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"bbox": [80.0, 12.8, 80.3, 13.1]}

    with patch.object(client.session, "request", return_value=mock_resp):
        res_dist = client.get_district_extent("D01")
        res_taluk = client.get_taluk_extent("T01")
        res_vil = client.get_village_extent("V01")

        assert "bbox" in res_dist
        assert "bbox" in res_taluk
        assert "bbox" in res_vil


def test_get_gis_attributes(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"attributes": {"survey_no": "104/2"}}

    with patch.object(client.session, "request", return_value=mock_resp) as mock_req:
        res = client.get_gis_attributes(12.9249, 80.1000, layer="cadastral")
        args, kwargs = mock_req.call_args
        assert kwargs["params"] == {"latitude": 12.9249, "longitude": 80.1000, "layer": "cadastral"}
        assert res["attributes"]["survey_no"] == "104/2"


def test_get_multi_feature_buffer(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"buffered_features": ["facility1", "gate2"]}

    with patch.object(client.session, "request", return_value=mock_resp) as mock_req:
        res = client.get_multi_feature_buffer(12.9249, 80.1000, buffer_meters=50.0)
        args, kwargs = mock_req.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["json"]["buffer_meters"] == 50.0
        assert "buffered_features" in res


def test_get_nearest_feature(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"nearest_feature": "Main Gate", "distance_meters": 12.4}

    with patch.object(client.session, "request", return_value=mock_resp) as mock_req:
        res = client.get_nearest_feature(12.9249, 80.1000, layer="gates")
        args, kwargs = mock_req.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["json"]["layer"] == "gates"
        assert res["nearest_feature"] == "Main Gate"


def test_check_inside_boundary(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"inside": True, "boundary_status": "INSIDE"}

    with patch.object(client.session, "request", return_value=mock_resp) as mock_req:
        res = client.check_inside_boundary(
            latitude=12.9249,
            longitude=80.1000,
            layer="workplace_boundary",
            boundary_id="BND_TAMBARAM",
        )
        args, kwargs = mock_req.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["json"]["layer"] == "workplace_boundary"
        assert kwargs["json"]["boundary_id"] == "BND_TAMBARAM"
        assert res["inside"] is True


def test_client_timeout_exception(client):
    with patch.object(client.session, "request", side_effect=requests.exceptions.Timeout("Read timeout")):
        with pytest.raises(TNGISTimeoutError) as exc_info:
            client.get_district_data()
        assert "timeout" in str(exc_info.value).lower()


def test_client_connection_error_exception(client):
    with patch.object(client.session, "request", side_effect=requests.exceptions.ConnectionError("Refused")):
        with pytest.raises(TNGISConnectionError) as exc_info:
            client.get_district_data()
        assert "connect" in str(exc_info.value).lower()


def test_client_http_404_error(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Boundary layer not found"

    with patch.object(client.session, "request", return_value=mock_resp):
        with pytest.raises(TNGISResponseError) as exc_info:
            client.get_district_extent("INVALID_CODE")
        assert exc_info.value.status_code == 404


def test_client_invalid_json(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body>Not JSON</body></html>"
    mock_resp.json.side_effect = ValueError("Invalid JSON")

    with patch.object(client.session, "request", return_value=mock_resp):
        with pytest.raises(TNGISResponseError) as exc_info:
            client.get_district_data()
        assert "invalid json" in str(exc_info.value).lower()

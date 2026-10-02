"""
Live Integration Tests for Module 5: GPS + GIS Location Verification.
Targets actual configured TNGIS endpoints.
Clearly separated as integration tests.
NEVER fabricates a successful response if live gateway is unreachable.
"""

import pytest
from app import config
from app.tngis_client import TNGISClient, TNGISClientError
from app.location_service import LocationService


@pytest.mark.integration
def test_live_tngis_gateway_probe():
    """
    Probes live TNGIS API gateway.
    Reports real network status without mock.
    """
    client = TNGISClient()
    try:
        data = client.get_district_data()
        assert isinstance(data, dict)
        assert "_latency_ms" in data
        print(f"\n[LIVE SUCCESS] TNGIS Gateway responded in {data['_latency_ms']}ms")
    except TNGISClientError as err:
        print(f"\n[LIVE PROBE REPORT] TNGIS Gateway unreachable at {config.TNGIS_BASE_URL}: {err}")
        pytest.skip(
            f"TNGIS API endpoint '{config.TNGIS_BASE_URL}' unreachable in current environment. "
            f"Government gateway may require whitelisted IP, intranet access, or active VPN. "
            f"Error details: {err}"
        )


@pytest.mark.integration
def test_live_location_verification_honesty():
    """
    Verifies that when live API is unreachable, verify_location strictly returns
    API_ERROR and NEVER falsely reports VERIFIED.
    """
    service = LocationService(tngis_client=TNGISClient())
    expected = {
        "workplace_id": "TEST_SITE",
        "boundary_id": "BND_001",
        "boundary_layer": "workplace_boundary",
    }

    result = service.verify(
        worker_id="W_LIVE_TEST",
        latitude=12.9249,
        longitude=80.1000,
        expected_location=expected,
    )

    if result.get("status") == "VERIFIED":
        # Live API is actually reachable and worker is inside
        assert result["location_verified"] is True
        assert result["boundary_check"] == "INSIDE"
    elif result.get("status") == "REJECTED":
        # Live API is reachable and worker is outside
        assert result["location_verified"] is False
        assert result["boundary_check"] == "OUTSIDE"
    else:
        # Live API was unreachable: MUST be API_ERROR
        assert result["status"] == "API_ERROR"
        assert result["location_verified"] is False
        assert result["boundary_check"] == "UNKNOWN"
        print(f"\n[LIVE API CHECK] Correctly caught live connection failure: {result.get('message')}")

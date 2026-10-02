"""
TNGIS API Client Layer
Handles all HTTP communication with the Tamil Nadu Geographical Information System (TNGIS) APIs.
Implements the 10 core administrative, spatial extent, attribute, and boundary services.
"""

import time
import logging
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import ConnectionError as ReqConnectionError
from requests.exceptions import Timeout as ReqTimeout
from requests.exceptions import RequestException

from app import config

logger = logging.getLogger("module5_gis.tngis_client")


class TNGISClientError(Exception):
    """Base exception for all TNGIS client operations."""
    pass


class TNGISConnectionError(TNGISClientError):
    """Raised when connection to TNGIS gateway fails (DNS, unreachable host, refused)."""
    pass


class TNGISTimeoutError(TNGISClientError):
    """Raised when TNGIS request exceeds configured timeout."""
    pass


class TNGISResponseError(TNGISClientError):
    """Raised when TNGIS returns HTTP 4xx, 5xx or unparseable payload."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class TNGISClient:
    """
    Dedicated HTTP Client for TNGIS spatial web services.
    Encapsulates endpoint routing, authentication headers, latency tracking, and error handling.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        app_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        verify_ssl: Optional[bool] = None,
    ):
        self.base_url = (base_url or config.TNGIS_BASE_URL).rstrip("/")
        self.app_name = app_name or config.TNGIS_APP_NAME
        self.api_key = api_key or config.TNGIS_API_KEY
        self.timeout = timeout or config.TNGIS_TIMEOUT_SECONDS
        self.verify_ssl = config.TNGIS_VERIFY_SSL if verify_ssl is None else verify_ssl

        self.session = requests.Session()
        self.session.headers.update(self._build_headers())

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"SmartAttendance-GISModule/1.0 ({self.app_name})",
            "X-App-Name": self.app_name,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        return headers

    def _send_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes an HTTP request against the TNGIS gateway with latency timing and error translation.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start_time = time.time()

        logger.info(f"Dispatching TNGIS request: {method} {url} | params={params}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            elapsed_ms = (time.time() - start_time) * 1000.0

            logger.info(
                f"TNGIS response received: HTTP {response.status_code} in {elapsed_ms:.1f}ms"
            )

            if response.status_code >= 400:
                raise TNGISResponseError(
                    f"TNGIS API returned HTTP {response.status_code}: {response.text[:200]}",
                    status_code=response.status_code,
                    response_text=response.text,
                )

            try:
                data = response.json()
            except ValueError as json_err:
                raise TNGISResponseError(
                    f"TNGIS API returned invalid JSON: {json_err}",
                    status_code=response.status_code,
                    response_text=response.text,
                )

            if isinstance(data, dict):
                data["_latency_ms"] = round(elapsed_ms, 2)
            return data

        except ReqTimeout as te:
            elapsed_ms = (time.time() - start_time) * 1000.0
            logger.error(f"TNGIS request timed out after {elapsed_ms:.1f}ms ({self.timeout}s limit): {te}")
            raise TNGISTimeoutError(
                f"TNGIS API timeout after {self.timeout} seconds for endpoint '{endpoint}'"
            ) from te

        except ReqConnectionError as ce:
            elapsed_ms = (time.time() - start_time) * 1000.0
            logger.error(f"TNGIS connection failed after {elapsed_ms:.1f}ms: {ce}")
            raise TNGISConnectionError(
                f"Could not connect to TNGIS API at {self.base_url}. Network or server unreachable."
            ) from ce

        except RequestException as re:
            elapsed_ms = (time.time() - start_time) * 1000.0
            logger.error(f"Unexpected TNGIS network error after {elapsed_ms:.1f}ms: {re}")
            raise TNGISClientError(f"TNGIS HTTP request failure: {re}") from re

    # --------------------------------------------------------------------------
    # 1. Administrative Data – District
    # --------------------------------------------------------------------------
    def get_district_data(
        self, district_code: Optional[str] = None, district_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch administrative data for Tamil Nadu districts."""
        params = {}
        if district_code:
            params["district_code"] = district_code
        if district_name:
            params["district_name"] = district_name
        return self._send_request("GET", "administrative/districts", params=params)

    # --------------------------------------------------------------------------
    # 2. Administrative Data – Taluk
    # --------------------------------------------------------------------------
    def get_taluk_data(
        self, district_code: str, taluk_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch taluk administrative records under a specific district."""
        params = {"district_code": district_code}
        if taluk_code:
            params["taluk_code"] = taluk_code
        return self._send_request("GET", "administrative/taluks", params=params)

    # --------------------------------------------------------------------------
    # 3. Administrative Data – Revenue Village
    # --------------------------------------------------------------------------
    def get_village_data(
        self, taluk_code: str, village_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch revenue village administrative records under a specific taluk."""
        params = {"taluk_code": taluk_code}
        if village_code:
            params["village_code"] = village_code
        return self._send_request("GET", "administrative/villages", params=params)

    # --------------------------------------------------------------------------
    # 4. District Spatial Extent
    # --------------------------------------------------------------------------
    def get_district_extent(self, district_code: str) -> Dict[str, Any]:
        """Fetch spatial bounding box coordinates for a district."""
        return self._send_request("GET", f"extent/district/{district_code}")

    # --------------------------------------------------------------------------
    # 5. Taluk Spatial Extent
    # --------------------------------------------------------------------------
    def get_taluk_extent(self, taluk_code: str) -> Dict[str, Any]:
        """Fetch spatial bounding box coordinates for a taluk."""
        return self._send_request("GET", f"extent/taluk/{taluk_code}")

    # --------------------------------------------------------------------------
    # 6. Revenue Village Spatial Extent
    # --------------------------------------------------------------------------
    def get_village_extent(self, village_code: str) -> Dict[str, Any]:
        """Fetch spatial bounding box coordinates for a revenue village."""
        return self._send_request("GET", f"extent/village/{village_code}")

    # --------------------------------------------------------------------------
    # 7. Attributes – GIS
    # --------------------------------------------------------------------------
    def get_gis_attributes(
        self, latitude: float, longitude: float, layer: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch GIS cadastral / jurisdictional attributes for a specific coordinate."""
        params = {"latitude": latitude, "longitude": longitude}
        if layer:
            params["layer"] = layer
        return self._send_request("GET", "features/attributes", params=params)

    # --------------------------------------------------------------------------
    # 8. Multi Feature Attributes – Based on Buffer
    # --------------------------------------------------------------------------
    def get_multi_feature_buffer(
        self,
        latitude: float,
        longitude: float,
        buffer_meters: float,
        layers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Query multi-feature attributes within a radius buffer from a point."""
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "buffer_meters": buffer_meters,
            "layers": layers or [],
        }
        return self._send_request("POST", "features/buffer-attributes", json_data=payload)

    # --------------------------------------------------------------------------
    # 9. Nearest Feature
    # --------------------------------------------------------------------------
    def get_nearest_feature(
        self,
        latitude: float,
        longitude: float,
        layer: Optional[str] = None,
        max_distance: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Find the nearest mapped feature (landmark, gate, boundary point) to a coordinate."""
        payload = {"latitude": latitude, "longitude": longitude}
        if layer:
            payload["layer"] = layer
        if max_distance:
            payload["max_distance_meters"] = max_distance
        return self._send_request("POST", "spatial/nearest-feature", json_data=payload)

    # --------------------------------------------------------------------------
    # 10. Inside Boundary
    # --------------------------------------------------------------------------
    def check_inside_boundary(
        self,
        latitude: float,
        longitude: float,
        layer: str,
        boundary_id: str,
        attribute_filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute core TNGIS Point-in-Polygon containment check.
        Evaluates whether (latitude, longitude) is geographically INSIDE or OUTSIDE
        the designated boundary polygon in layer `layer` identified by `boundary_id`.
        """
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "layer": layer,
            "boundary_id": boundary_id,
            "attribute_filters": attribute_filters or {},
        }
        return self._send_request("POST", "spatial/inside-boundary", json_data=payload)

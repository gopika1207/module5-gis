"""
Boundary Verification Service
Interprets expected boundary definitions, performs Point-in-Polygon validation
against TNGIS layer services, and normalizes GIS boundary outcomes.
"""

import logging
from typing import Any, Dict, Optional, Tuple
from app.tngis_client import TNGISClient, TNGISClientError

logger = logging.getLogger("module5_gis.boundary_service")


class BoundaryService:
    """
    Executes boundary containment checks using TNGIS spatial services.
    """

    def __init__(self, client: Optional[TNGISClient] = None):
        self.client = client or TNGISClient()

    def verify_boundary(
        self,
        latitude: float,
        longitude: float,
        expected_location: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validates whether a coordinate point falls inside the expected boundary.

        :param latitude: Validated worker latitude
        :param longitude: Validated worker longitude
        :param expected_location: Metadata dictionary specifying allowed boundaries:
            - boundary_id: (str) Unique boundary ID or workplace ID
            - boundary_layer: (str) GIS layer name (e.g. 'workplace_boundary', 'revenue_village')
            - district: (str, optional) Expected District name
            - taluk: (str, optional) Expected Taluk name
            - village: (str, optional) Expected Revenue Village
            - attribute_filters: (dict, optional) Extra query filters
        :return: Standardized boundary result dict
        """
        boundary_id = str(
            expected_location.get("boundary_id")
            or expected_location.get("workplace_id")
            or expected_location.get("village_code")
            or expected_location.get("village")
            or "DEFAULT_BOUNDARY"
        )
        layer = str(
            expected_location.get("boundary_layer")
            or expected_location.get("layer")
            or "workplace_boundary"
        )

        attribute_filters = expected_location.get("attribute_filters") or {}
        if "district" in expected_location and "district" not in attribute_filters:
            attribute_filters["district"] = expected_location["district"]
        if "taluk" in expected_location and "taluk" not in attribute_filters:
            attribute_filters["taluk"] = expected_location["taluk"]
        if "village" in expected_location and "village" not in attribute_filters:
            attribute_filters["village"] = expected_location["village"]

        logger.info(
            f"Evaluating boundary containment: point=({latitude}, {longitude}), "
            f"layer={layer}, boundary_id={boundary_id}"
        )

        # Execute real TNGIS Point-in-Polygon check
        tngis_resp = self.client.check_inside_boundary(
            latitude=latitude,
            longitude=longitude,
            layer=layer,
            boundary_id=boundary_id,
            attribute_filters=attribute_filters,
        )

        inside, boundary_status = self._parse_containment_response(tngis_resp)

        # Extract returned GIS details
        tngis_attrs = tngis_resp.get("attributes") or tngis_resp.get("feature_attributes") or {}
        district = (
            tngis_attrs.get("district")
            or tngis_resp.get("district")
            or expected_location.get("district")
            or "Unknown District"
        )
        taluk = (
            tngis_attrs.get("taluk")
            or tngis_resp.get("taluk")
            or expected_location.get("taluk")
            or "Unknown Taluk"
        )
        village = (
            tngis_attrs.get("village")
            or tngis_attrs.get("revenue_village")
            or tngis_resp.get("village")
            or expected_location.get("village")
            or "Unknown Village"
        )

        latency_ms = tngis_resp.get("_latency_ms", 0.0)

        return {
            "inside": inside,
            "boundary_check": boundary_status,
            "boundary_id": boundary_id,
            "layer": layer,
            "district": district,
            "taluk": taluk,
            "village": village,
            "latency_ms": latency_ms,
            "raw_response": tngis_resp,
        }

    def _parse_containment_response(self, response: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Normalizes polymorphic TNGIS response fields into (is_inside: bool, status: 'INSIDE'|'OUTSIDE').
        """
        # 1. Direct boolean flags
        if "inside" in response:
            is_inside = bool(response["inside"])
            return is_inside, "INSIDE" if is_inside else "OUTSIDE"

        if "is_inside" in response:
            is_inside = bool(response["is_inside"])
            return is_inside, "INSIDE" if is_inside else "OUTSIDE"

        # 2. String status values
        status_val = str(
            response.get("boundary_check")
            or response.get("status")
            or response.get("containment")
            or ""
        ).upper()

        if status_val in ("INSIDE", "WITHIN", "CONTAINED", "VERIFIED", "SUCCESS"):
            return True, "INSIDE"
        if status_val in ("OUTSIDE", "EXCLUDED", "REJECTED"):
            return False, "OUTSIDE"

        # 3. Check features list (if GeoJSON or WFS-style response)
        features = response.get("features")
        if isinstance(features, list):
            if len(features) > 0:
                return True, "INSIDE"
            return False, "OUTSIDE"

        # Default fallback if unknown response format
        return False, "OUTSIDE"

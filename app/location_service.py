"""
Location Verification Service
Core orchestration engine for Module 5: GPS + GIS Location Verification.
Performs strict WGS 84 coordinate validation, interacts with the TNGIS boundary service,
and returns clean standardized verification decisions for Student 2 (Backend API).
"""

import logging
from typing import Any, Dict, Optional, Union
from app import config
from app.tngis_client import (
    TNGISClient,
    TNGISClientError,
    TNGISConnectionError,
    TNGISTimeoutError,
    TNGISResponseError,
)
from app.boundary_service import BoundaryService

logger = logging.getLogger("module5_gis.location_service")


class LocationService:
    """
    Validates GPS inputs, triggers GIS point-in-polygon verification via TNGIS,
    and returns production-grade attendance decisions.
    """

    def __init__(
        self,
        tngis_client: Optional[TNGISClient] = None,
        boundary_service: Optional[BoundaryService] = None,
    ):
        self.tngis_client = tngis_client or TNGISClient()
        self.boundary_service = boundary_service or BoundaryService(client=self.tngis_client)

    def validate_inputs(
        self,
        worker_id: Any,
        latitude: Any,
        longitude: Any,
        expected_location: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Validates worker_id, numerical coordinates, and expected_location.
        Returns an error response dictionary if invalid, or None if valid.
        """
        # 1. Validate worker_id
        if not worker_id or not isinstance(worker_id, str) or not worker_id.strip():
            return {
                "worker_id": str(worker_id) if worker_id else None,
                "latitude": latitude,
                "longitude": longitude,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": "Missing or invalid worker_id. Must be a non-empty string.",
            }

        # 2. Validate latitude
        try:
            lat_float = float(latitude)
        except (ValueError, TypeError):
            return {
                "worker_id": worker_id.strip(),
                "latitude": latitude,
                "longitude": longitude,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": f"Invalid latitude value: '{latitude}'. Must be a valid float.",
            }

        if lat_float < config.MIN_LATITUDE or lat_float > config.MAX_LATITUDE:
            return {
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": longitude,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": f"Latitude {lat_float} out of range. Must be between -90.0 and 90.0.",
            }

        # 3. Validate longitude
        try:
            lon_float = float(longitude)
        except (ValueError, TypeError):
            return {
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": longitude,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": f"Invalid longitude value: '{longitude}'. Must be a valid float.",
            }

        if lon_float < config.MIN_LONGITUDE or lon_float > config.MAX_LONGITUDE:
            return {
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": lon_float,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": f"Longitude {lon_float} out of range. Must be between -180.0 and 180.0.",
            }

        # 4. Validate expected_location
        if not expected_location or not isinstance(expected_location, dict):
            return {
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": lon_float,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": "Missing or invalid expected_location. Must be a non-empty dictionary.",
            }

        return None

    def verify(
        self,
        worker_id: str,
        latitude: Union[float, int, str],
        longitude: Union[float, int, str],
        expected_location: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes full location verification pipeline.
        Never maps an API error to VERIFIED.
        """
        # Step 1: Input Validation
        validation_error = self.validate_inputs(worker_id, latitude, longitude, expected_location)
        if validation_error:
            logger.warning(f"Validation failed for worker {worker_id}: {validation_error['message']}")
            return validation_error

        worker_id_clean = worker_id.strip()
        lat_clean = float(latitude)
        lon_clean = float(longitude)

        logger.info(
            f"Verifying worker '{worker_id_clean}' at coordinates ({lat_clean}, {lon_clean}) "
            f"against boundary specification: {expected_location}"
        )

        # Step 2: Query TNGIS boundary containment
        try:
            boundary_result = self.boundary_service.verify_boundary(
                latitude=lat_clean,
                longitude=lon_clean,
                expected_location=expected_location,
            )

            is_inside = boundary_result["inside"]
            boundary_check = boundary_result["boundary_check"]
            district = boundary_result["district"]
            taluk = boundary_result["taluk"]
            village = boundary_result["village"]
            latency_ms = boundary_result.get("latency_ms", 0.0)

            if is_inside:
                logger.info(f"Worker '{worker_id_clean}' VERIFIED inside permitted boundary ({district}, {taluk}, {village}).")
                return {
                    "worker_id": worker_id_clean,
                    "latitude": lat_clean,
                    "longitude": lon_clean,
                    "location_verified": True,
                    "status": "VERIFIED",
                    "boundary_check": "INSIDE",
                    "district": district,
                    "taluk": taluk,
                    "village": village,
                    "boundary_id": boundary_result.get("boundary_id"),
                    "api_status": "SUCCESS",
                    "latency_ms": latency_ms,
                    "message": "Worker is inside the permitted boundary.",
                }
            else:
                logger.warning(f"Worker '{worker_id_clean}' REJECTED outside permitted boundary ({boundary_check}).")
                return {
                    "worker_id": worker_id_clean,
                    "latitude": lat_clean,
                    "longitude": lon_clean,
                    "location_verified": False,
                    "status": "REJECTED",
                    "boundary_check": "OUTSIDE",
                    "district": district,
                    "taluk": taluk,
                    "village": village,
                    "boundary_id": boundary_result.get("boundary_id"),
                    "api_status": "SUCCESS",
                    "latency_ms": latency_ms,
                    "message": "Worker is outside the permitted boundary.",
                }

        except TNGISTimeoutError as toe:
            logger.error(f"API Timeout error during verification for worker '{worker_id_clean}': {toe}")
            return {
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "location_verified": False,
                "status": "API_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "TIMEOUT",
                "error_type": "TNGISTimeoutError",
                "message": f"TNGIS API request timed out: {toe}",
            }

        except TNGISConnectionError as coe:
            logger.error(f"Connection failure to TNGIS for worker '{worker_id_clean}': {coe}")
            return {
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "location_verified": False,
                "status": "API_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "CONNECTION_FAILED",
                "error_type": "TNGISConnectionError",
                "message": f"TNGIS connection failed: {coe}",
            }

        except TNGISResponseError as rpe:
            logger.error(f"HTTP error from TNGIS for worker '{worker_id_clean}': {rpe}")
            return {
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "location_verified": False,
                "status": "API_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "HTTP_ERROR",
                "http_status_code": rpe.status_code,
                "error_type": "TNGISResponseError",
                "message": f"TNGIS service returned error: {rpe}",
            }

        except TNGISClientError as tce:
            logger.error(f"General TNGIS client error for worker '{worker_id_clean}': {tce}")
            return {
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "location_verified": False,
                "status": "API_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "CLIENT_ERROR",
                "error_type": "TNGISClientError",
                "message": f"TNGIS verification error: {tce}",
            }

        except Exception as ex:
            logger.exception(f"Unexpected exception during verification for worker '{worker_id_clean}': {ex}")
            return {
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "location_verified": False,
                "status": "INTERNAL_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "ERROR",
                "error_type": type(ex).__name__,
                "message": f"Unexpected verification failure: {ex}",
            }


# Default singleton instance for quick module access
_default_service = LocationService()


def verify_location(
    worker_id: str,
    latitude: Union[float, int, str],
    longitude: Union[float, int, str],
    expected_location: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Public integration function for Student 2 (Backend API).
    Standard entry-point matching the contract:
        verify_location(worker_id, latitude, longitude, expected_location)
    """
    return _default_service.verify(
        worker_id=worker_id,
        latitude=latitude,
        longitude=longitude,
        expected_location=expected_location,
    )

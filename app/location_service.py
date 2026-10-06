#!/usr/bin/env python
"""
Location Verification Service
Core orchestration engine for Module 5: GPS + GIS Location Verification.

Project:
Smart Attendance and Field Activity Monitoring System

Student 5:
GPS + GIS Location Verification

Responsibilities:
- Validate worker ID
- Validate latitude / longitude
- Validate GPS accuracy
- Verify worker location against permitted GIS boundary
- Return standardized JSON response for backend integration
- Never convert TNGIS/API errors into VERIFIED status
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
    Validates GPS inputs, triggers GIS point-in-polygon verification
    via TNGIS, and returns standardized attendance decisions.
    """

    def __init__(
        self,
        tngis_client: Optional[TNGISClient] = None,
        boundary_service: Optional[BoundaryService] = None,
    ):
        self.tngis_client = tngis_client or TNGISClient()
        self.boundary_service = boundary_service or BoundaryService(
            client=self.tngis_client
        )

    # ============================================================
    # INPUT VALIDATION
    # ============================================================

    def validate_inputs(
        self,
        worker_id: Any,
        latitude: Any,
        longitude: Any,
        gps_accuracy: Any,
        expected_location: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Validate worker ID, GPS coordinates, GPS accuracy,
        and expected location.

        Returns:
            Error response dictionary if invalid.
            None if all inputs are valid.
        """

        # --------------------------------------------------------
        # 1. Validate worker_id
        # --------------------------------------------------------

        if not worker_id or not isinstance(worker_id, str) or not worker_id.strip():
            return {
                "success": False,
                "worker_id": str(worker_id) if worker_id else None,
                "latitude": latitude,
                "longitude": longitude,
                "gps_accuracy": gps_accuracy,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": (
                    "Missing or invalid worker_id. "
                    "Must be a non-empty string."
                ),
            }

        # --------------------------------------------------------
        # 2. Validate latitude
        # --------------------------------------------------------

        try:
            lat_float = float(latitude)
        except (ValueError, TypeError):
            return {
                "success": False,
                "worker_id": worker_id.strip(),
                "latitude": latitude,
                "longitude": longitude,
                "gps_accuracy": gps_accuracy,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": (
                    f"Invalid latitude value: '{latitude}'. "
                    "Must be a valid float."
                ),
            }

        if (
            lat_float < config.MIN_LATITUDE
            or lat_float > config.MAX_LATITUDE
        ):
            return {
                "success": False,
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": longitude,
                "gps_accuracy": gps_accuracy,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": (
                    f"Latitude {lat_float} out of range. "
                    "Must be between -90.0 and 90.0."
                ),
            }

        # --------------------------------------------------------
        # 3. Validate longitude
        # --------------------------------------------------------

        try:
            lon_float = float(longitude)
        except (ValueError, TypeError):
            return {
                "success": False,
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": longitude,
                "gps_accuracy": gps_accuracy,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": (
                    f"Invalid longitude value: '{longitude}'. "
                    "Must be a valid float."
                ),
            }

        if (
            lon_float < config.MIN_LONGITUDE
            or lon_float > config.MAX_LONGITUDE
        ):
            return {
                "success": False,
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": lon_float,
                "gps_accuracy": gps_accuracy,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": (
                    f"Longitude {lon_float} out of range. "
                    "Must be between -180.0 and 180.0."
                ),
            }

        # --------------------------------------------------------
        # 4. Validate GPS accuracy
        # --------------------------------------------------------

        try:
            accuracy_float = float(gps_accuracy)
        except (ValueError, TypeError):
            return {
                "success": False,
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": lon_float,
                "gps_accuracy": gps_accuracy,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": (
                    f"Invalid gps_accuracy value: '{gps_accuracy}'. "
                    "Must be a non-negative number in meters."
                ),
            }

        if accuracy_float < 0:
            return {
                "success": False,
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": lon_float,
                "gps_accuracy": accuracy_float,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": (
                    "GPS accuracy cannot be negative."
                ),
            }

        # --------------------------------------------------------
        # 5. Validate expected_location
        # --------------------------------------------------------

        if (
            not expected_location
            or not isinstance(expected_location, dict)
        ):
            return {
                "success": False,
                "worker_id": worker_id.strip(),
                "latitude": lat_float,
                "longitude": lon_float,
                "gps_accuracy": accuracy_float,
                "location_verified": False,
                "status": "VALIDATION_ERROR",
                "boundary_check": "INVALID",
                "message": (
                    "Missing or invalid expected_location. "
                    "Must be a non-empty dictionary."
                ),
            }

        return None

    # ============================================================
    # LOCATION VERIFICATION
    # ============================================================

    def verify(
        self,
        worker_id: str,
        latitude: Union[float, int, str],
        longitude: Union[float, int, str],
        gps_accuracy: Union[float, int, str],
        expected_location: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the complete location verification pipeline.

        IMPORTANT:
        TNGIS/API errors are NEVER mapped to VERIFIED.
        """

        # --------------------------------------------------------
        # Step 1: Input Validation
        # --------------------------------------------------------

        validation_error = self.validate_inputs(
            worker_id,
            latitude,
            longitude,
            gps_accuracy,
            expected_location,
        )

        if validation_error:
            logger.warning(
                f"Validation failed for worker {worker_id}: "
                f"{validation_error['message']}"
            )
            return validation_error

        worker_id_clean = worker_id.strip()
        lat_clean = float(latitude)
        lon_clean = float(longitude)
        accuracy_clean = float(gps_accuracy)

        logger.info(
            f"Verifying worker '{worker_id_clean}' "
            f"at coordinates ({lat_clean}, {lon_clean}) "
            f"with GPS accuracy {accuracy_clean} meters "
            f"against boundary specification: {expected_location}"
        )

        # --------------------------------------------------------
        # Step 2: Query TNGIS boundary containment
        # --------------------------------------------------------

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

            latency_ms = boundary_result.get(
                "latency_ms",
                0.0,
            )

            # ====================================================
            # INSIDE BOUNDARY
            # ====================================================

            if is_inside:

                logger.info(
                    f"Worker '{worker_id_clean}' VERIFIED "
                    f"inside permitted boundary "
                    f"({district}, {taluk}, {village})."
                )

                return {
                    "success": True,
                    "worker_id": worker_id_clean,
                    "latitude": lat_clean,
                    "longitude": lon_clean,
                    "gps_accuracy": accuracy_clean,
                    "location_verified": True,
                    "status": "VERIFIED",
                    "boundary_check": "INSIDE",
                    "district": district,
                    "taluk": taluk,
                    "village": village,
                    "boundary_id": boundary_result.get(
                        "boundary_id"
                    ),
                    "api_status": "SUCCESS",
                    "latency_ms": latency_ms,
                    "message": (
                        "Worker is inside the permitted boundary."
                    ),
                }

            # ====================================================
            # OUTSIDE BOUNDARY
            # ====================================================

            else:

                logger.warning(
                    f"Worker '{worker_id_clean}' REJECTED "
                    f"outside permitted boundary "
                    f"({boundary_check})."
                )

                return {
                    "success": True,
                    "worker_id": worker_id_clean,
                    "latitude": lat_clean,
                    "longitude": lon_clean,
                    "gps_accuracy": accuracy_clean,
                    "location_verified": False,
                    "status": "REJECTED",
                    "boundary_check": "OUTSIDE",
                    "district": district,
                    "taluk": taluk,
                    "village": village,
                    "boundary_id": boundary_result.get(
                        "boundary_id"
                    ),
                    "api_status": "SUCCESS",
                    "latency_ms": latency_ms,
                    "message": (
                        "Worker is outside the permitted boundary."
                    ),
                }

        # ========================================================
        # TNGIS TIMEOUT
        # ========================================================

        except TNGISTimeoutError as toe:

            logger.error(
                f"API Timeout error during verification "
                f"for worker '{worker_id_clean}': {toe}"
            )

            return {
                "success": False,
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "gps_accuracy": accuracy_clean,
                "location_verified": False,
                "status": "API_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "TIMEOUT",
                "error_type": "TNGISTimeoutError",
                "message": f"TNGIS API request timed out: {toe}",
            }

        # ========================================================
        # TNGIS CONNECTION ERROR
        # ========================================================

        except TNGISConnectionError as coe:

            logger.error(
                f"Connection failure to TNGIS "
                f"for worker '{worker_id_clean}': {coe}"
            )

            return {
                "success": False,
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "gps_accuracy": accuracy_clean,
                "location_verified": False,
                "status": "API_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "CONNECTION_FAILED",
                "error_type": "TNGISConnectionError",
                "message": f"TNGIS connection failed: {coe}",
            }

        # ========================================================
        # TNGIS HTTP RESPONSE ERROR
        # ========================================================

        except TNGISResponseError as rpe:

            logger.error(
                f"HTTP error from TNGIS "
                f"for worker '{worker_id_clean}': {rpe}"
            )

            return {
                "success": False,
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "gps_accuracy": accuracy_clean,
                "location_verified": False,
                "status": "API_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "HTTP_ERROR",
                "http_status_code": rpe.status_code,
                "error_type": "TNGISResponseError",
                "message": f"TNGIS service returned error: {rpe}",
            }

        # ========================================================
        # GENERAL TNGIS CLIENT ERROR
        # ========================================================

        except TNGISClientError as tce:

            logger.error(
                f"General TNGIS client error "
                f"for worker '{worker_id_clean}': {tce}"
            )

            return {
                "success": False,
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "gps_accuracy": accuracy_clean,
                "location_verified": False,
                "status": "API_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "CLIENT_ERROR",
                "error_type": "TNGISClientError",
                "message": f"TNGIS verification error: {tce}",
            }

        # ========================================================
        # UNEXPECTED ERROR
        # ========================================================

        except Exception as ex:

            logger.exception(
                f"Unexpected exception during verification "
                f"for worker '{worker_id_clean}': {ex}"
            )

            return {
                "success": False,
                "worker_id": worker_id_clean,
                "latitude": lat_clean,
                "longitude": lon_clean,
                "gps_accuracy": accuracy_clean,
                "location_verified": False,
                "status": "INTERNAL_ERROR",
                "boundary_check": "UNKNOWN",
                "api_status": "ERROR",
                "error_type": type(ex).__name__,
                "message": f"Unexpected verification failure: {ex}",
            }


# ================================================================
# DEFAULT SERVICE INSTANCE
# ================================================================

_default_service = LocationService()


# ================================================================
# PUBLIC INTEGRATION FUNCTION
# ================================================================

def verify_location(
    worker_id: str,
    latitude: Union[float, int, str],
    longitude: Union[float, int, str],
    gps_accuracy: Union[float, int, str],
    expected_location: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Public integration function for Student 2 Backend API.

    Standard entry point:

        verify_location(
            worker_id,
            latitude,
            longitude,
            gps_accuracy,
            expected_location
        )
    """

    return _default_service.verify(
        worker_id=worker_id,
        latitude=latitude,
        longitude=longitude,
        gps_accuracy=gps_accuracy,
        expected_location=expected_location,
    )
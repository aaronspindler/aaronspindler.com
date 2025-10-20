"""
API views for FeeFiFoFunds.

Provides REST API endpoints for fund data, analysis, and comparison.
"""

from django.db import connection
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView


@extend_schema(
    description="API root endpoint showing available API routes",
    responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request, format=None):
    """
    API Root endpoint.

    Returns links to all available API endpoints.
    """
    return Response(
        {
            "message": "FeeFiFoFunds API v1",
            "endpoints": {
                "health": reverse("api:health-check", request=request, format=format),
                "docs": {
                    "swagger": request.build_absolute_uri("/api/docs/"),
                    "redoc": request.build_absolute_uri("/api/redoc/"),
                    "schema": request.build_absolute_uri("/api/schema/"),
                },
                "coming_soon": {
                    "funds": "API endpoints will be available after FUND-024",
                    "comparison": "API endpoints will be available after FUND-025",
                    "auth": "Authentication endpoints will be available after FUND-028",
                },
            },
            "version": "1.0.0",
            "timestamp": timezone.now().isoformat(),
        }
    )


class HealthCheckView(APIView):
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        - 200 OK if all systems are operational
        - 503 Service Unavailable if critical systems are down
    """

    permission_classes = [AllowAny]

    @extend_schema(
        description="Health check endpoint for monitoring",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "checks": {
                        "type": "object",
                        "properties": {
                            "database": {"type": "string"},
                            "api": {"type": "string"},
                        },
                    },
                },
            },
            503: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "error": {"type": "string"},
                },
            },
        },
    )
    def get(self, request, format=None):
        """
        Perform health checks on critical systems.

        Checks:
        - Database connectivity
        - API availability

        Returns:
            Response with status and check results
        """
        checks = {}
        is_healthy = True

        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {str(e)}"
            is_healthy = False

        # API check (always ok if we got here)
        checks["api"] = "ok"

        response_data = {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": timezone.now().isoformat(),
            "checks": checks,
        }

        status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(response_data, status=status_code)

"""
Authentication views for FeeFiFoFunds API.

Implements FUND-028: Authentication & Authorization
Provides JWT token endpoints and user management.

Note: Requires djangorestframework-simplejwt (added in FUND-023)
"""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()


# Use the built-in Simple JWT views
# These are already configured in settings.py (from FUND-023)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view with additional user information.

    POST /api/v1/auth/token/
    {
        "username": "user",
        "password": "pass"
    }

    Returns:
    {
        "access": "eyJ...",
        "refresh": "eyJ...",
        "user": {
            "id": 1,
            "username": "user",
            "email": "user@example.com"
        }
    }
    """

    @extend_schema(
        description="Obtain JWT access and refresh tokens",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                },
                "required": ["username", "password"],
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                    "user": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "username": {"type": "string"},
                            "email": {"type": "string"},
                        },
                    },
                },
            }
        },
    )
    def post(self, request, *args, **kwargs):
        """Override to add user information to response."""
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Add user information to response
            user = User.objects.get(username=request.data.get("username"))
            response.data["user"] = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }

        return response


@extend_schema(
    description="Get current user profile",
    responses={
        200: {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "username": {"type": "string"},
                "email": {"type": "string"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "date_joined": {"type": "string"},
            },
        }
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get current authenticated user information.

    GET /api/v1/auth/me/

    Returns user profile data.
    """
    user = request.user

    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined.isoformat(),
        }
    )


@extend_schema(
    description="Logout and blacklist refresh token",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "refresh": {"type": "string"},
            },
            "required": ["refresh"],
        }
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
            },
        }
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def logout(request):
    """
    Logout by blacklisting the refresh token.

    POST /api/v1/auth/logout/
    {
        "refresh": "eyJ..."
    }

    Blacklists the refresh token to prevent further use.
    """
    try:
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    description="Check authentication status",
    responses={
        200: {
            "type": "object",
            "properties": {
                "authenticated": {"type": "boolean"},
                "username": {"type": "string"},
            },
        }
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def auth_status(request):
    """
    Check if user is authenticated.

    GET /api/v1/auth/status/

    Returns authentication status and username if authenticated.
    """
    if request.user.is_authenticated:
        return Response(
            {
                "authenticated": True,
                "username": request.user.username,
            }
        )
    else:
        return Response(
            {
                "authenticated": False,
                "username": None,
            }
        )

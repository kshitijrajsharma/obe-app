import os

import toml
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView


@extend_schema(
    summary="API root endpoint",
    description="Returns API version information and documentation links.",
    responses={
        200: {
            "type": "object",
            "properties": {
                "api_version": {"type": "string"},
                "docs": {"type": "string", "format": "uri"},
                "schema": {"type": "string", "format": "uri"},
                "redoc": {"type": "string", "format": "uri"},
            },
        }
    },
)
class APIRootView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        version = "unknown"
        pyproject_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "pyproject.toml",
        )
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                pyproject = toml.load(f)
                version = pyproject.get("project", {}).get("version", "unknown")
        except Exception:
            pass
        return Response(
            {
                "api_version": version,
                "docs": request.build_absolute_uri("/api/docs/"),
                "schema": request.build_absolute_uri("/api/schema/"),
                "redoc": request.build_absolute_uri("/api/redoc/"),
            }
        )

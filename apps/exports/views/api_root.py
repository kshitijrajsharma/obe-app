import os

import toml
from rest_framework.response import Response
from rest_framework.views import APIView


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

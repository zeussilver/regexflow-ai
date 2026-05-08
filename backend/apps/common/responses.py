from rest_framework import status
from rest_framework.response import Response


def error_response(
    code: str,
    message: str,
    http_status: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
            }
        },
        status=http_status,
    )

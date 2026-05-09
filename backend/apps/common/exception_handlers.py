from rest_framework.exceptions import (
    MethodNotAllowed,
    ParseError,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.views import exception_handler


ERROR_CODES = {
    ParseError: "PARSE_ERROR",
    MethodNotAllowed: "METHOD_NOT_ALLOWED",
    UnsupportedMediaType: "UNSUPPORTED_MEDIA_TYPE",
    ValidationError: "VALIDATION_ERROR",
}

ERROR_MESSAGES = {
    ParseError: "Malformed request body.",
    ValidationError: "The request could not be validated.",
}


def structured_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if _has_structured_error(response.data):
        return response

    response.data = {
        "error": {
            "code": _error_code(exc),
            "message": _error_message(exc),
        }
    }
    return response


def _has_structured_error(data):
    return isinstance(data, dict) and isinstance(data.get("error"), dict)


def _error_code(exc):
    for exc_class, code in ERROR_CODES.items():
        if isinstance(exc, exc_class):
            return code

    default_code = getattr(exc, "default_code", None)
    if default_code:
        return str(default_code).upper()

    return "API_ERROR"


def _error_message(exc):
    for exc_class, message in ERROR_MESSAGES.items():
        if isinstance(exc, exc_class):
            return message

    detail = getattr(exc, "detail", None)
    if isinstance(detail, (list, dict)):
        return "The request could not be processed."

    return str(detail or exc) or "The request could not be processed."

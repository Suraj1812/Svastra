from typing import Any, Optional


def success_response(data: Any = None, message: Optional[str] = None):
    return {
        "success": True,
        "data": data,
        "message": message,
        "error": None,
    }


def error_response(code: str, message: str, details: Any = None, request_id: Optional[str] = None):
    return {
        "success": False,
        "data": None,
        "message": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        },
    }

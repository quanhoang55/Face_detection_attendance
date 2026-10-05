"""Route dependencies backed by application state."""

from fastapi import Request

from backend.main import CoreServices


def get_core(request: Request) -> CoreServices:
    return request.app.state.core

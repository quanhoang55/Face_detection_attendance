"""Small synchronous client for Supabase's PostgREST Data API."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SupabaseRequestError(RuntimeError):
    def __init__(self, message: str, *, code: str | None = None, status: int = 0):
        super().__init__(message)
        self.code = code
        self.status = status


class SupabaseRestClient:
    """Minimal PostgREST client; credentials are only held on the backend."""

    def __init__(self, url: str, secret_key: str, timeout: float = 15.0) -> None:
        self._base_url = f"{url.rstrip('/')}/rest/v1"
        self._secret_key = secret_key
        self._timeout = timeout

    def request(
        self,
        method: str,
        table: str,
        *,
        query: dict[str, str] | None = None,
        payload: object | None = None,
        prefer: str | None = None,
    ) -> list[dict[str, object]]:
        url = f"{self._base_url}/{table}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {
            "apikey": self._secret_key,
            "Authorization": f"Bearer {self._secret_key}",
            "Accept": "application/json",
        }
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload, allow_nan=False).encode("utf-8")
        if prefer:
            headers["Prefer"] = prefer
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
        except HTTPError as error:
            raw_error = error.read()
            try:
                details = json.loads(raw_error)
            except (json.JSONDecodeError, UnicodeDecodeError):
                details = {}
            raise SupabaseRequestError(
                str(details.get("message", f"Supabase request failed ({error.code})")),
                code=details.get("code"),
                status=error.code,
            ) from error
        except (URLError, TimeoutError) as error:
            raise SupabaseRequestError("Could not reach Supabase") from error

        if not raw:
            return []
        decoded = json.loads(raw)
        if not isinstance(decoded, list):
            raise SupabaseRequestError("Supabase returned an unexpected response")
        return decoded

"""Actuent — the search engine for AI agents.

    from actuent import Actuent
    client = Actuent()                      # free tier, or Actuent(api_key="ak_...") for Pro
    results = client.search("barber amsterdam")
    shoes = client.search("running shoes under €100")["products"]
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

__version__ = "0.1.0"
__all__ = ["Actuent", "ActuentError", "RateLimitError"]

_USER_AGENT = f"actuent-python/{__version__}"


class ActuentError(Exception):
    """An error response from Actuent."""

    def __init__(self, message: str, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class RateLimitError(ActuentError):
    """Too many requests. `retry_after` is the number of seconds to wait."""

    def __init__(self, message: str, retry_after: Optional[int] = None, body: Any = None):
        super().__init__(message, 429, body)
        self.retry_after = retry_after


class Actuent:
    """Client for the Actuent API (https://docs.actuent.ai).

    api_key: optional Pro key from actuent.ai. Defaults to the ACTUENT_API_KEY environment variable.
    Without a key you get the free tier (20 requests/minute).
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.actuent.ai",
                 agents_url: str = "https://agents.actuent.ai", timeout: float = 60.0):
        self.api_key = api_key if api_key is not None else os.environ.get("ACTUENT_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.agents_url = agents_url.rstrip("/")
        self.timeout = timeout
        self.rate_limit: Dict[str, Optional[int]] = {}

    def _request(self, method: str, url: str, body: Optional[Dict[str, Any]] = None) -> Any:
        headers = {"Accept": "application/json", "User-Agent": _USER_AGENT}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                self._remember_limits(response.headers)
                return json.loads(response.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as error:
            self._remember_limits(error.headers)
            try:
                payload = json.loads(error.read().decode("utf-8") or "null")
            except ValueError:
                payload = None
            message = (payload or {}).get("error") or (payload or {}).get("message") or f"HTTP {error.code}"
            if error.code == 429:
                retry = error.headers.get("Retry-After")
                raise RateLimitError(message, int(retry) if retry and retry.isdigit() else None, payload) from None
            raise ActuentError(message, error.code, payload) from None

    def _remember_limits(self, headers: Any) -> None:
        def number(name: str) -> Optional[int]:
            value = headers.get(name) if headers else None
            return int(value) if value and str(value).isdigit() else None
        self.rate_limit = {"limit": number("X-RateLimit-Limit"), "remaining": number("X-RateLimit-Remaining"),
                           "reset": number("X-RateLimit-Reset")}

    def search(self, query: str) -> Dict[str, Any]:
        """Search by topic, domain or page, in any language. Returns {"results": [...LAWP], "products": [...]}.

        Examples: "barber amsterdam", "nike.com", "stripe.com/pricing", "running shoes under €100".
        """
        return self._request("GET", f"{self.base_url}/api/search?q={urllib.parse.quote(query)}")

    def get_site(self, domain: str) -> Optional[Dict[str, Any]]:
        """The LAWP for one site (or None if Actuent can't find it)."""
        results = self.search(domain).get("results") or []
        return results[0] if results else None

    def get_page(self, url: str) -> Optional[Dict[str, Any]]:
        """The LAWP for one page, e.g. "stripe.com/pricing"."""
        return self.get_site(url)

    def products(self, query: str) -> list:
        """Products with prices, e.g. "running shoes under €100"."""
        return self.search(query).get("products") or []

    def check_site(self, domain: str) -> Dict[str, Any]:
        """Validate a site's /.well-known/lawp.json and its action endpoints."""
        return self._request("GET", f"{self.agents_url}/api/lawp-check?domain={urllib.parse.quote(domain)}")

    def register(self, site: Dict[str, Any]) -> Dict[str, Any]:
        """List or update your own site's LAWP (Pro key, verified domain). See docs.actuent.ai/#sdk."""
        return self._request("POST", f"{self.base_url}/api/register", site)

    def state(self) -> Dict[str, Any]:
        """Live "State of the AI web" statistics."""
        return self._request("GET", f"{self.base_url}/api/state")

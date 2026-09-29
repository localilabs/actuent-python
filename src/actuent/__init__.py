"""Actuent — the search engine for AI agents.

    from actuent import Actuent
    client = Actuent()                      # free tier, or Actuent(api_key="ak_...") for Pro
    results = client.search("barber amsterdam")
    shoes = client.search("running shoes under €100")["products"]
    evening = client.plan("Nørreport, Copenhagen", stops=["dinner", "drinks"])
    fade = client.find_service("skin fade under €30", location="Amsterdam")
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

__version__ = "0.7.0"
__all__ = ["Actuent", "ActuentError", "RateLimitError", "BusyError"]

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


class BusyError(ActuentError):
    """Actuent is very busy right now (HTTP 503). `retry_after` is the number of seconds to wait;
    the message is written for people, so it can be shown as is."""

    def __init__(self, message: str, retry_after: Optional[int] = None, body: Any = None):
        super().__init__(message, 503, body)
        self.retry_after = retry_after


class Actuent:
    """Client for the Actuent API (https://docs.actuent.ai).

    api_key: optional Pro key from actuent.ai. Defaults to the ACTUENT_API_KEY environment variable.
    Without a key you get the free tier (20 requests/minute).
    retries: when Actuent is busy (429/503), wait as long as it asks (at most 60s) and try again,
    this many times. Default 1; 0 turns it off.

    Search results that are limited or empty include "message" and "notices", in plain English:
    show "message" to the user. See https://docs.actuent.ai/#errors
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.actuent.ai",
                 agents_url: str = "https://agents.actuent.ai", timeout: float = 60.0, retries: int = 1):
        self.api_key = api_key if api_key is not None else os.environ.get("ACTUENT_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.agents_url = agents_url.rstrip("/")
        self.timeout = timeout
        self.rate_limit: Dict[str, Optional[int]] = {}
        self.retries = max(0, retries)

    def _request(self, method: str, url: str, body: Optional[Dict[str, Any]] = None) -> Any:
        for attempt in range(self.retries + 1):
            try:
                return self._request_once(method, url, body)
            except (RateLimitError, BusyError) as error:
                if attempt >= self.retries:
                    raise
                time.sleep(min(error.retry_after or 30, 60))

    def _request_once(self, method: str, url: str, body: Optional[Dict[str, Any]] = None) -> Any:
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
            message = (payload or {}).get("message") or (payload or {}).get("error") or f"HTTP {error.code}"
            retry = error.headers.get("Retry-After")
            retry_after = int(retry) if retry and retry.isdigit() else (payload or {}).get("retry_after_seconds")
            if error.code == 429:
                raise RateLimitError(message, retry_after, payload) from None
            if error.code == 503:
                raise BusyError(message, retry_after, payload) from None
            raise ActuentError(message, error.code, payload) from None

    def _remember_limits(self, headers: Any) -> None:
        def number(name: str) -> Optional[int]:
            value = headers.get(name) if headers else None
            return int(value) if value and str(value).isdigit() else None
        self.rate_limit = {"limit": number("X-RateLimit-Limit"), "remaining": number("X-RateLimit-Remaining"),
                           "reset": number("X-RateLimit-Reset")}

    def search(self, query: str, **options: Any) -> Dict[str, Any]:
        """Search by topic, domain or page, in any language. Returns {"results": [...LAWP], "products": [...]}.

        Examples: "barber amsterdam", "nike.com", "stripe.com/pricing", "running shoes under €100".
        Options: limit, offset, category, city, lang, open_now=True, sort="relevance"|"popular"|"fresh".
        Results have "snippet", "score" (0-100) and "matched"; the response may have "did_you_mean",
        "related", "events", "places", "products", a plain-English "message", "comparison" (for
        "notion vs obsidian": {"sites", "tip"}) and "answer" (for "does basecamp have a free plan":
        {"domain", "sentences": [{"text", "url"}], "note"}).
        """
        params = {"q": query}
        params.update({k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in options.items() if v is not None})
        return self._request("GET", f"{self.base_url}/api/search?{urllib.parse.urlencode(params)}")

    def ask(self, domain: str, question: str) -> Dict[str, Any]:
        """Answer a question from one site's own pages ("is there parking?"):
        {"sentences": [{"text", "url"}], "actions": [...], "note" or "message"}."""
        return self._request("GET", f"{self.base_url}/api/ask?domain={urllib.parse.quote(domain)}&q={urllib.parse.quote(question)}")

    def similar(self, domain: str, limit: int = 10) -> Dict[str, Any]:
        """Sites like this one ("sites like notion.so"): {"sites": [{"domain", "name", "category", "why"}]}."""
        return self._request("GET", f"{self.base_url}/api/similar?domain={urllib.parse.quote(domain)}&limit={int(limit)}")

    def autocomplete(self, prefix: str) -> Dict[str, Any]:
        """Sites and searches that start with what's typed: {"sites": [...], "searches": [...]}."""
        return self._request("GET", f"{self.base_url}/api/autocomplete?q={urllib.parse.quote(prefix)}")

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

    # ----- Tools from the Actuent MCP server (the same ones ChatGPT and Claude use) -----

    def _tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        args = {k: v for k, v in arguments.items() if v is not None}
        reply = self._request("POST", f"{self.agents_url}/api/mcp",
                              {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})
        if not isinstance(reply, dict) or "result" not in reply:
            raise ActuentError((reply or {}).get("error", {}).get("message", "Unexpected response"), None, reply)
        result = reply["result"]
        text = "".join(part.get("text", "") for part in result.get("content", []) if part.get("type") == "text")
        try:
            data = json.loads(text)
        except ValueError:
            data = text
        if result.get("isError"):
            message = (data.get("message") or data.get("error")) if isinstance(data, dict) else str(data)
            raise ActuentError(message or f"{name} failed", None, data)
        return data

    def get_actions(self, domain: str) -> Dict[str, Any]:
        """A site's actions, whether each is executable, and the JSON Schema of each input."""
        return self._tool("actuent_get_actions", {"domain": domain})

    def ask_site(self, domain: str, question: str) -> Dict[str, Any]:
        """Answer a question from one site's own pages, e.g. ("nike.com", "free returns?")."""
        return self._tool("actuent_ask_site", {"domain": domain, "question": question})

    def nearby(self, query: str, location: str, radius_metres: Optional[int] = None, open_now: Optional[bool] = None,
               filters: Optional[list] = None) -> Dict[str, Any]:
        """Places near a location. filters: vegan, vegetarian, gluten_free, wheelchair, outdoor_seating, wifi, kids, dogs."""
        return self._tool("actuent_nearby", {"query": query, "location": location, "radius_metres": radius_metres,
                                             "open_now": open_now, "filters": filters})

    def find_service(self, query: str, location: Optional[str] = None, max_price: Optional[float] = None,
                     currency: Optional[str] = None) -> Dict[str, Any]:
        """A service or dish with its price at local businesses, e.g. "skin fade under €30"."""
        return self._tool("actuent_find_service", {"query": query, "location": location, "max_price": max_price, "currency": currency})

    def plan(self, location: str, stops: Optional[list] = None, date: Optional[str] = None, start_time: Optional[str] = None,
             cuisine: Optional[str] = None, filters: Optional[list] = None) -> Dict[str, Any]:
        """A timed outing, e.g. stops=["dinner", "drinks"] from 19:00, with places open when you'd arrive."""
        return self._tool("actuent_plan", {"location": location, "stops": stops, "date": date, "start_time": start_time,
                                           "cuisine": cuisine, "filters": filters})

    def trip(self, location: str, days: int = 2, start_date: Optional[str] = None, filters: Optional[list] = None) -> Dict[str, Any]:
        """A 1–4 day city trip: where to stay and a plan for each day."""
        return self._tool("actuent_trip", {"location": location, "days": days, "start_date": start_date, "filters": filters})

    def events(self, location: Optional[str] = None, query: Optional[str] = None, date_from: Optional[str] = None,
               date_to: Optional[str] = None) -> Dict[str, Any]:
        """Upcoming events that websites publish, by city, topic and dates (YYYY-MM-DD)."""
        return self._tool("actuent_events", {"location": location, "query": query, "from": date_from, "to": date_to})

    def compare_sites(self, domains: list) -> Any:
        """Compare two or more sites side by side."""
        return self._tool("actuent_compare", {"domains": domains})

    def compare_products(self, urls: list) -> Dict[str, Any]:
        """Compare products by URL: price, stock, 90-day price range and cheaper shops."""
        return self._tool("actuent_compare", {"products": urls})

    def news(self, topic: str) -> Any:
        """Latest articles on a topic."""
        return self._tool("actuent_news", {"topic": topic})

    def watch_price(self, url: str, target_price_eur: Optional[float] = None, notify: str = "price",
                    webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """(Pro) Get an email, and optionally a webhook, when a product's price drops or it's back in stock
        (notify="price", "stock" or "both")."""
        return self._tool("actuent_watch_price", {"url": url, "target_price_eur": target_price_eur, "notify": notify, "webhook_url": webhook_url})

    def price_watches(self) -> Dict[str, Any]:
        """(Pro) Your price watches."""
        return self._tool("actuent_watch_price", {"action": "list"})

    def execute_action(self, domain: str, action_id: str, input: Any = None, mode: str = "execute",
                       confirmed: Optional[bool] = None) -> Dict[str, Any]:
        """(Pro) Perform a site's action.

        Actions that cost money or ask for confirmation first return needs_confirmation: show the
        user the details, then call again with confirmed=True. mode="quote" returns price and
        availability without committing. Long-running actions return pending with a status_url.
        """
        return self._tool("actuent_execute_action", {"domain": domain, "action_id": action_id, "input": input,
                                                     "mode": mode, "confirmed": confirmed})

    def action_status(self, domain: str, status_url: str) -> Dict[str, Any]:
        """(Pro) Check a long-running action that returned pending."""
        return self._tool("actuent_action_status", {"domain": domain, "status_url": status_url})

    # ----- Scores and badges -----

    def score(self, domain: str) -> Dict[str, Any]:
        """A site's agent-readiness score (0–100), label, category and checks."""
        return self._request("GET", f"{self.base_url}/badge.json?domain={urllib.parse.quote(domain)}")

    def leaderboard(self) -> Dict[str, Any]:
        """The 100 sites agents found most often this week."""
        return self._request("GET", f"{self.base_url}/leaderboard")

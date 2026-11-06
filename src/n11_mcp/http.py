"""HTTP layer for n11_mcp.

n11.com answers HTTP 200 to plain HTTP clients with a browser UA
(verified live 2026-11-06: homepage, search, product pages). The
transport still uses curl-cffi chrome120 impersonation, the same proven
pattern as the other Turkey-factory servers, so a stricter bot check
does not break the server overnight. Requests are kept gentle (one at
a time, ~0.8s apart) and read-only.
"""
from __future__ import annotations

import time
from urllib.parse import quote_plus, urlparse

from curl_cffi import requests as _r

BASE = "https://www.n11.com"
TIMEOUT = 30.0
MIN_INTERVAL = 0.8  # seconds between requests — be polite

_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

_last_fetch = 0.0


class N11Error(RuntimeError):
    pass


def _get(url: str) -> str:
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = _r.get(url, impersonate="chrome120", headers=_HEADERS, timeout=TIMEOUT)
    except Exception as e:
        raise N11Error(f"network error fetching {url}: {e}") from e
    finally:
        _last_fetch = time.monotonic()
    if resp.status_code == 403:
        raise N11Error(
            "n11.com refused the request (HTTP 403, bot wall) — try again later"
        )
    if resp.status_code == 429:
        raise N11Error(
            "n11.com rate-limited the request (HTTP 429) — try again later"
        )
    if resp.status_code == 404:
        raise N11Error(f"page not found (HTTP 404): {url}")
    if resp.status_code != 200:
        raise N11Error(f"unexpected HTTP {resp.status_code} fetching {url}")
    return resp.text


def fetch_search_html(query: str, sort_param: str | None = None, page: int = 1) -> str:
    """Search page HTML. sort_param: 'PRICE_LOW' (price asc) or 'PRICE_HIGH'."""
    url = f"{BASE}/arama?q={quote_plus(query)}"
    if sort_param:
        url += f"&srt={sort_param}"
    if page > 1:
        url += f"&pg={page}"
    return _get(url)


def fetch_product_html(product: str) -> str:
    """Product page HTML. product: full URL or site path '/urun/<slug>-<id>'."""
    path = product.strip()
    if path.startswith("http"):
        parsed = urlparse(path)
        if "n11.com" not in parsed.netloc:
            raise N11Error("product must be an n11.com URL or path")
        path = parsed.path
    if not path.startswith("/"):
        path = "/" + path
    if "/urun/" not in path:
        raise N11Error(
            "product must be a product URL/path containing '/urun/…' "
            "(find one with n11_search first)"
        )
    return _get(f"{BASE}{path}")


def fetch_home_html() -> str:
    return _get(f"{BASE}/")

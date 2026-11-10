"""MCP server: unofficial read-only access to n11.com shopping."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import http as _http
from . import products as _P

mcp = FastMCP("n11-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for n11.com, Türkiye's #3 marketplace.
Data comes from the site's public server-rendered pages: search pages
carry a schema.org ItemList JSON-LD block (20 products: title, price in
TRY, list price, brand, SKU, image, stock), product pages carry a
schema.org Product JSON-LD block (price, rating, review count, reviews,
images) plus a breadcrumb category path and a seller block (company,
store name, authorized-store badge, seller grade), and the homepage
carries the 11 top categories. Product URLs look like
"/urun/apple-iphone-17-pro-max-256-gb-apple-turkiye-garantili-100816929"
(the trailing number is the product id; use n11_search to find product
URLs). Prices are in Turkish Lira (TRY) unless noted. Search sorts:
relevance (default), price_asc (cheapest first), price_desc (most
expensive first). Read-only, no login, no API key. Transport uses
Chrome TLS impersonation; the server spaces requests ~0.8s apart.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — Turkey MCP factory.\
"""


_SOURCE = "n11.com"
_DISCLAIMER = "Unofficial read-only data from n11.com; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


def _validate_limit(limit: int) -> int:
    if not 1 <= limit <= 24:
        raise ValueError("limit must be between 1 and 24")
    return limit


@mcp.tool()
def n11_search(query: str, limit: int = 10, sort: str = "relevance", page: int = 1) -> str:
    """Search n11.com products by keyword. query: Turkish or ASCII,
    e.g. "iphone", "kablosuz kulaklık", "laptop". sort: "relevance"
    (default), "price_asc" (cheapest first), "price_desc" (most
    expensive first). limit 1..24; page 1-based. Returns title, price
    in TRY, list price, brand, SKU, product URL, image and stock
    status per product."""
    try:
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        _validate_limit(limit)
        if page < 1:
            raise ValueError("page must be >= 1")
        sort_param = _P.resolve_sort(sort)
        html = _http.fetch_search_html(query.strip(), sort_param=sort_param, page=page)
        rows = _P.parse_search_results(html, limit=limit)
    except (ValueError, _http.N11Error) as e:
        return _err(e)
    return _ok({"query": query.strip(), "sort": sort, "page": page,
         "count": len(rows), "products": rows})


@mcp.tool()
def n11_product_detail(product: str) -> str:
    """Detail of one product: name, brand, price in TRY, list price,
    stock status, rating and review count, seller (company, store name,
    authorized-store badge, grade), category path, description, images.
    product: a full product URL or site path containing "/urun/…" (find
    one with n11_search first), e.g.
    "/urun/apple-iphone-17-pro-max-256-gb-apple-turkiye-garantili-100816929"."""
    try:
        html = _http.fetch_product_html(product)
        detail = _P.parse_product_detail(html)
    except (ValueError, _http.N11Error) as e:
        return _err(e)
    return _ok(detail)


@mcp.tool()
def n11_list_categories() -> str:
    """Top categories of n11.com (11 main categories): Turkish name,
    category URL and slug."""
    try:
        html = _http.fetch_home_html()
        cats = _P.parse_categories(html)
    except _http.N11Error as e:
        return _err(e)
    return _ok({"count": len(cats), "categories": cats})


@mcp.tool()
def n11_price_stats(query: str, limit: int = 24, sort: str = "relevance") -> str:
    """Price statistics for a search query: product count, min / median /
    mean / max price in TRY across the first page of results.
    query: e.g. "iphone 15"; limit 1..24 (default 24 = whole first page)."""
    try:
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        _validate_limit(limit)
        sort_param = _P.resolve_sort(sort)
        html = _http.fetch_search_html(query.strip(), sort_param=sort_param)
        rows = _P.parse_search_results(html, limit=limit)
        stats = _P.price_stats(rows)
    except (ValueError, _http.N11Error) as e:
        return _err(e)
    return _ok({"query": query.strip(), "sort": sort, **stats})


@mcp.tool()
def n11_product_reviews(product: str, limit: int = 5) -> str:
    """Recent customer reviews of one product: reviewer and star rating.
    (n11 does not server-render review bodies, so only author + rating
    are returned.) product: a full product URL or site path containing
    "/urun/…" (find one with n11_search first). limit 1..24."""
    try:
        _validate_limit(limit)
        html = _http.fetch_product_html(product)
        reviews = _P.parse_reviews(html, limit=limit)
    except (ValueError, _http.N11Error) as e:
        return _err(e)
    return _ok({"product": product, "count": len(reviews), "reviews": reviews})


@mcp.tool()
def n11_health() -> str:
    """Check whether n11.com is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

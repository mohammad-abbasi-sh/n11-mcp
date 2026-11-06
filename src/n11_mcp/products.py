"""Stdlib parsing for n11.com server-rendered pages.

Verified live 2026-11-06 against real pages:
- Search (/arama?q=…): a schema.org ItemList JSON-LD block with 20
  products per page (name, url, image list, sku, brand, offers with
  price / list price / availability). Sort params srt=PRICE_LOW /
  PRICE_HIGH verified live (prices ascend / first is max); paging pg=N
  verified live (page 2 returns different SKUs).
- Product page (/urun/<slug>-<id>): a schema.org Product JSON-LD
  block (name, brand, sku, description, image, offers, aggregateRating
  with ratingValue/reviewCount, review list with author + rating), a
  BreadcrumbList inside the WebPage JSON-LD (category path), and an
  embedded seller JSON object ("seller":{companyName, nickName,
  officialSellerText, ...}, "sellerGrade":100).
- Homepage: top-category nav <nav data-layoutname="homepageDesktopMenu">
  with <li class="catMenuItem"> items (href + <h2> name), 11 categories.
"""
from __future__ import annotations

import html as _html
import json
import re
import statistics

BASE = "https://www.n11.com"

SORTS = {
    "relevance": None,          # n11 default
    "price_asc": "PRICE_LOW",   # verified live: first prices ascend
    "price_desc": "PRICE_HIGH",  # verified live: first price is max
}


def resolve_sort(sort: str) -> str | None:
    if sort not in SORTS:
        raise ValueError(
            f"unknown sort {sort!r} (expected one of: {', '.join(SORTS)})"
        )
    return SORTS[sort]


def parse_tr_number(text: str) -> float:
    """Turkish number: '112.434' -> 112434.0, '112.434,28' -> 112434.28."""
    s = text.strip().replace("\u00a0", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    return float(s)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def _ldjson_docs(html: str) -> list:
    docs = []
    for m in re.finditer(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S
    ):
        try:
            docs.append(json.loads(m.group(1)))
        except (json.JSONDecodeError, ValueError):
            continue
    return docs


def _walk(obj):
    """Yield every dict inside a parsed JSON document."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _find_typed(html: str, type_name: str) -> dict | None:
    for doc in _ldjson_docs(html):
        for node in _walk(doc):
            if node.get("@type") == type_name:
                return node
    return None


# ---------------------------------------------------------------- search

def parse_search_results(html: str, limit: int = 10) -> list[dict]:
    """Parse the search-page ItemList JSON-LD. Returns de-duplicated products."""
    item_list = _find_typed(html, "ItemList")
    if not item_list:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for element in item_list.get("itemListElement") or []:
        item = element.get("item") or {}
        if item.get("@type") != "Product":
            continue
        sku = str(item.get("sku") or "")
        if not sku or sku in seen:
            continue
        seen.add(sku)
        name = item.get("name")
        offers = item.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = offers.get("price")
        if not name or price is None:
            continue
        try:
            price_try = float(price)
        except (TypeError, ValueError):
            continue
        brand = item.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        images = item.get("image") or []
        if isinstance(images, str):
            images = [images]
        availability = str(offers.get("availability") or "")
        row: dict = {
            "title": _html.unescape(str(name)).strip(),
            "url": item.get("url"),
            "sku": sku,
            "brand": brand,
            "price_try": price_try,
            "price_currency": offers.get("priceCurrency") or "TRY",
            "in_stock": ("InStock" in availability) if availability else None,
        }
        spec = offers.get("priceSpecification") or {}
        if isinstance(spec, dict) and spec.get("price") is not None:
            try:
                row["original_price_try"] = float(spec["price"])
            except (TypeError, ValueError):
                pass
        if images:
            row["image"] = images[0]
        out.append({k: v for k, v in row.items() if v is not None})
        if len(out) >= limit:
            break
    return out


def price_stats(products: list[dict]) -> dict:
    prices = sorted(p["price_try"] for p in products if p.get("price_try") is not None)
    if not prices:
        return {"count": 0}
    return {
        "count": len(prices),
        "min_try": prices[0],
        "median_try": round(statistics.median(prices), 2),
        "mean_try": round(sum(prices) / len(prices), 2),
        "max_try": prices[-1],
    }


# ---------------------------------------------------------------- detail

def _extract_seller(html: str) -> dict:
    """Parse the embedded seller JSON object (balanced braces)."""
    i = html.find('"seller":{')
    if i < 0:
        return {}
    j = i + len('"seller":')
    start = j
    depth = 0
    while j < len(html):
        c = html[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                j += 1
                break
        j += 1
    try:
        seller = json.loads(html[start:j])
    except (json.JSONDecodeError, ValueError):
        return {}
    grade_m = re.search(r'"sellerGrade":\s*(\d+)', html[j:j + 120])
    out: dict = {}
    if seller.get("companyName"):
        out["seller_company"] = seller["companyName"]
    if seller.get("nickName"):
        out["seller"] = seller["nickName"]
    if seller.get("officialSellerText"):
        out["seller_badge"] = seller["officialSellerText"]
    if grade_m:
        out["seller_grade"] = int(grade_m.group(1))
    # shipmentCity / shipmentCondition are siblings of the seller object.
    tail = html[j:j + 1500]
    city_m = re.search(r'"shipmentCity":\s*"([^"]+)"', tail)
    if city_m:
        out["shipment_city"] = city_m.group(1)
    cond_m = re.search(r'"shipmentCondition":\s*"([^"]+)"', tail)
    if cond_m:
        out["shipment_condition"] = cond_m.group(1)
    return out


def parse_product_detail(html: str) -> dict:
    product = _find_typed(html, "Product")
    if not product:
        raise ValueError("no schema.org Product data found on this page")
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    rating = product.get("aggregateRating") or {}
    brand = product.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")
    price = offers.get("price")
    try:
        price_try = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_try = None
    availability = str(offers.get("availability") or "")
    images = product.get("image") or []
    if isinstance(images, str):
        images = [images]
    detail: dict = {
        "name": product.get("name"),
        "sku": str(product.get("sku")) if product.get("sku") is not None else None,
        "brand": brand,
        "description": product.get("description"),
        "price_try": price_try,
        "price_currency": offers.get("priceCurrency") or "TRY",
        "in_stock": ("InStock" in availability) if availability else None,
        "rating": (
            float(rating.get("ratingValue"))
            if rating.get("ratingValue") is not None
            else None
        ),
        "review_count": (
            int(str(rating.get("reviewCount") or 0).replace(".", ""))
            if rating.get("reviewCount") is not None
            else None
        ),
        "images": images[:5],
        "url": offers.get("url"),
    }
    spec = offers.get("priceSpecification") or {}
    if isinstance(spec, dict) and spec.get("price") is not None:
        try:
            detail["original_price_try"] = float(spec["price"])
        except (TypeError, ValueError):
            pass
    # Category path from the WebPage BreadcrumbList (skip Anasayfa + product).
    webpage = _find_typed(html, "WebPage")
    if webpage:
        crumb = webpage.get("breadcrumb") or {}
        elements = crumb.get("itemListElement") or []
        names = [
            (el.get("item") or {}).get("name")
            for el in elements
            if isinstance(el.get("item"), dict)
        ]
        names = [n for n in names if n]
        if len(names) > 2:
            detail["category"] = " > ".join(names[1:-1])
    detail.update(_extract_seller(html))
    return {k: v for k, v in detail.items() if v is not None}


def parse_reviews(html: str, limit: int = 5) -> list[dict]:
    """Reviews from the Product JSON-LD (author + star rating; n11 does not
    server-render review bodies)."""
    product = _find_typed(html, "Product")
    if not product:
        return []
    out: list[dict] = []
    for node in product.get("review") or []:
        if not isinstance(node, dict):
            continue
        author = node.get("author")
        if isinstance(author, dict):
            author = author.get("name")
        rr = node.get("reviewRating") or {}
        out.append(
            {
                "author": author,
                "rating": (
                    float(rr.get("ratingValue"))
                    if rr.get("ratingValue") is not None
                    else None
                ),
            }
        )
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- categories

_CAT_RE = re.compile(
    r'<li class="catMenuItem"[^>]*><a href="([^"]+)"[^>]*>'
    r'.*?<h2 class="catMenuItem-text"[^>]*>([^<]+)</h2>',
    re.S,
)


def parse_categories(html: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for m in _CAT_RE.finditer(html):
        path, name = m.group(1), _clean(m.group(2))
        if not name or path in seen:
            continue
        seen.add(path)
        out.append(
            {
                "name": name,
                "url": BASE + path,
                "slug": path.strip("/"),
            }
        )
    return out

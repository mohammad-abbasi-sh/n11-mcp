# n11-mcp 🇹🇷

> ⚠️ **Status: PARTIALLY DEGRADED (2026-11-10)** — n11.com's bot wall intermittently blocks the search path (/arama) from this environment (about 1 in 3 searches succeed; fingerprint rotation recovered the homepage). Homepage, categories and health checks work reliably. Search and price-stats tools may return a "blocked — try again later" error; retrying sometimes succeeds. Check `n11_health` for the live status.


mcp-name: io.github.mohammad-abbasi-sh/n11-mcp

Unofficial **read-only** MCP server for **n11.com**, Türkiye's #3 marketplace — search millions of products, read product details (price, list price, stock, rating, seller, category), read customer reviews, browse the 11 top categories, and get price statistics (min / median / mean / max) for any query.

> Built by Mohammad Abbasi as part of the "Turkey MCP factory" (Sepehr-style pipeline). Not affiliated with n11.com.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "n11": {
      "command": "uvx",
      "args": ["n11-mcp==0.1.1"]
    }
  }
}
```

Or run locally: `python -m n11_mcp.server` (needs `mcp<2`, `curl-cffi`).

## Tools

| Tool | Description |
|------|-------------|
| `n11_search` | Search products by keyword — `query` ("iphone", "kablosuz kulaklık"), `sort` ("relevance" / "price_asc" / "price_desc"), `limit` 1..24, `page` 1-based; returns title, price in TRY, list price, brand, SKU, URL, image, stock status |
| `n11_product_detail` | Detail of one product (`product` = full URL or path with "/urun/…"): name, brand, price in TRY, list price, stock status, rating, review count, seller (company, store name, authorized-store badge, grade, shipment city), category path, description, images |
| `n11_list_categories` | The 11 top categories: Turkish name, URL, slug |
| `n11_price_stats` | Price statistics for a query: count, min / median / mean / max price in TRY across the first page |
| `n11_product_reviews` | Recent customer reviews of one product: reviewer and star rating (n11 does not server-render review bodies) |

Example output (`n11_search` / "iphone"):

```json
{"query": "iphone", "sort": "relevance", "page": 1, "count": 10, "products": [
  {"title": "Apple iPhone 17 Pro Max 256 GB (Apple Türkiye Garantili)",
   "url": "https://www.n11.com/urun/apple-iphone-17-pro-max-256-gb-apple-turkiye-garantili-100816929",
   "sku": "127340433485", "brand": "Apple", "price_try": 112434.28,
   "original_price_try": 117119.04, "price_currency": "TRY",
   "in_stock": true, "image": "https://n11scdn.akamaized.net/…"}, …]}
```

Example output (`n11_product_detail` / iPhone 17 Pro Max):

```json
{"name": "Apple iPhone 17 Pro Max 256 GB (Apple Türkiye Garantili) Turuncu 256 GB Fiyatları ve Özellikleri",
 "sku": "127340433485", "brand": "Apple", "price_try": 112434.28,
 "original_price_try": 117119.04, "price_currency": "TRY", "in_stock": true,
 "rating": 5.0, "review_count": 227,
 "category": "Elektronik > Telefon & Aksesuarları > Cep Telefonu > Apple Cep Telefonu",
 "seller_company": "SALİM TEKEMEN", "seller": "TKMNBILISIM",
 "seller_badge": "Yetkili Mağaza", "seller_grade": 100,
 "shipment_city": "Antalya", "shipment_condition": "Ücretsiz Kargo", …}
```

Example output (`n11_price_stats` / "iphone"):

```json
{"query": "iphone", "sort": "relevance", "count": 10, "min_try": 57199.0,
 "median_try": 106099.49, "mean_try": 100880.09, "max_try": 150999.55}
```

## How it works

n11.com answers plain HTTP clients, and the transport uses Chrome TLS
impersonation (`curl-cffi`, `chrome120`) so a stricter bot check does not
break the server. There is no public JSON API — data comes from the
site's server-rendered pages: search pages carry a schema.org ItemList
JSON-LD block (20 products per page), product pages carry a schema.org
Product JSON-LD block plus a breadcrumb category path and an embedded
seller JSON object, and the homepage carries the 11 top categories.
Requests are spaced ~0.8s apart; everything is read-only, no login,
no API key.

## Install

```bash
uvx n11-mcp==0.1.1        # run directly (needs uv)
# or
pip install n11-mcp==0.1.1
n11-mcp            # starts the MCP server on stdio
```

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Offline tests run on recorded fixtures (real pages fetched 2026-11-06);
live tests hit n11.com.

## Roadmap

- Category-scoped search (search within one category slug)
- Other sellers of the same product (compare prices per seller)
- Price history (track a SKU over days)

## License

MIT — see [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)

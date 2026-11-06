"""Live tests for n11_mcp — real requests to n11.com.

Requires network + Chrome TLS impersonation (curl-cffi). The server is
polite by design (~0.8s between requests), so this file takes ~10s.
Run: python -m unittest discover -s tests -v
"""
import json
import unittest

from n11_mcp import http as H
from n11_mcp import products as P

KNOWN_PRODUCT = "/urun/apple-iphone-17-pro-max-256-gb-apple-turkiye-garantili-100816929"


class TestLiveSearch(unittest.TestCase):
    def test_search_iphone(self):
        html = H.fetch_search_html("iphone")
        rows = P.parse_search_results(html, limit=3)
        self.assertGreaterEqual(len(rows), 1)
        first = rows[0]
        self.assertTrue(first["title"])
        self.assertTrue(first["price_try"] > 0)
        self.assertTrue(first["sku"])
        self.assertTrue(first["url"].startswith("https://www.n11.com/urun/"))

    def test_search_price_asc_order(self):
        html = H.fetch_search_html("iphone", sort_param="PRICE_LOW")
        rows = P.parse_search_results(html, limit=10)
        self.assertGreaterEqual(len(rows), 2)
        prices = [r["price_try"] for r in rows]
        self.assertEqual(prices, sorted(prices))

    def test_search_price_desc_first_is_max(self):
        html = H.fetch_search_html("iphone", sort_param="PRICE_HIGH")
        rows = P.parse_search_results(html, limit=10)
        self.assertGreaterEqual(len(rows), 2)
        prices = [r["price_try"] for r in rows]
        self.assertEqual(prices[0], max(prices))

    def test_search_page_two_differs(self):
        page1 = P.parse_search_results(H.fetch_search_html("iphone"), limit=10)
        page2 = P.parse_search_results(H.fetch_search_html("iphone", page=2), limit=10)
        skus1 = {r["sku"] for r in page1}
        skus2 = {r["sku"] for r in page2}
        self.assertTrue(skus1)
        self.assertTrue(skus2)
        self.assertFalse(skus1 & skus2)

    def test_search_no_results_shape(self):
        # A nonsense query returns a page; parser must not crash.
        html = H.fetch_search_html("zzzxqqqwwwnonexistent")
        rows = P.parse_search_results(html, limit=5)
        self.assertIsInstance(rows, list)


class TestLiveDetail(unittest.TestCase):
    def test_known_product(self):
        html = H.fetch_product_html(KNOWN_PRODUCT)
        d = P.parse_product_detail(html)
        self.assertIn("iPhone 17 Pro Max", d["name"])
        self.assertEqual(d["sku"], "127340433485")
        self.assertTrue(d["price_try"] > 0)
        self.assertEqual(d["price_currency"], "TRY")
        self.assertIn("Cep Telefonu", d.get("category", ""))

    def test_known_product_reviews(self):
        html = H.fetch_product_html(KNOWN_PRODUCT)
        reviews = P.parse_reviews(html, limit=3)
        self.assertGreaterEqual(len(reviews), 1)
        self.assertIsNotNone(reviews[0]["rating"])

    def test_bad_product_path(self):
        with self.assertRaises(H.N11Error):
            H.fetch_product_html("not-a-product-path")


class TestLiveCategoriesAndStats(unittest.TestCase):
    def test_categories(self):
        cats = P.parse_categories(H.fetch_home_html())
        self.assertGreaterEqual(len(cats), 5)
        names = [c["name"] for c in cats]
        self.assertIn("Elektronik", names)

    def test_price_stats(self):
        html = H.fetch_search_html("iphone")
        rows = P.parse_search_results(html, limit=10)
        stats = P.price_stats(rows)
        self.assertGreaterEqual(stats["count"], 1)
        self.assertLessEqual(stats["min_try"], stats["median_try"])
        self.assertLessEqual(stats["median_try"], stats["max_try"])


class TestLiveToolsEndToEnd(unittest.TestCase):
    """Exercise the MCP tool functions themselves (they hit the network)."""

    def test_search_tool_json(self):
        from n11_mcp.server import n11_search

        out = json.loads(n11_search("iphone", limit=2))
        self.assertEqual(out["query"], "iphone")
        self.assertEqual(out["count"], 2)
        self.assertTrue(out["products"][0]["price_try"] > 0)

    def test_stats_tool_json(self):
        from n11_mcp.server import n11_price_stats

        out = json.loads(n11_price_stats("iphone", limit=5))
        self.assertGreaterEqual(out["count"], 1)
        self.assertLessEqual(out["min_try"], out["max_try"])

    def test_bad_sort_tool_error_json(self):
        from n11_mcp.server import n11_search

        out = json.loads(n11_search("iphone", sort="nope"))
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()

"""Offline tests for n11_mcp.products — recorded real pages.

Fixtures are trimmed excerpts of real n11.com pages fetched
2026-11-06 (search "iphone", iPhone 17 Pro Max product page, homepage).
"""
import asyncio
import os
import unittest

from n11_mcp import products as P

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


class TestTrNumbers(unittest.TestCase):
    def test_price_formats(self):
        self.assertEqual(P.parse_tr_number("112.434"), 112434.0)
        self.assertEqual(P.parse_tr_number("112.434,28"), 112434.28)
        self.assertEqual(P.parse_tr_number("1.234,56"), 1234.56)
        self.assertEqual(P.parse_tr_number("4,8"), 4.8)
        self.assertEqual(P.parse_tr_number("599"), 599.0)

    def test_bad_number(self):
        with self.assertRaises(ValueError):
            P.parse_tr_number("abc")


class TestSearchParse(unittest.TestCase):
    def setUp(self):
        self.html = _read("search-iphone.html")

    def test_ten_products_limited(self):
        rows = P.parse_search_results(self.html, limit=10)
        self.assertEqual(len(rows), 10)

    def test_first_product(self):
        rows = P.parse_search_results(self.html, limit=10)
        first = rows[0]
        self.assertEqual(
            first["title"], "Apple iPhone 17 Pro Max 256 GB (Apple Türkiye Garantili)"
        )
        self.assertEqual(first["sku"], "127340433485")
        self.assertEqual(
            first["url"],
            "https://www.n11.com/urun/apple-iphone-17-pro-max-256-gb-apple-turkiye-garantili-100816929",
        )
        self.assertEqual(first["brand"], "Apple")
        self.assertEqual(first["price_try"], 112434.28)
        self.assertEqual(first["original_price_try"], 117119.04)
        self.assertEqual(first["price_currency"], "TRY")
        self.assertTrue(first["in_stock"])
        self.assertTrue(first["image"].startswith("https://n11scdn.akamaized.net/"))

    def test_second_product(self):
        rows = P.parse_search_results(self.html, limit=10)
        self.assertEqual(rows[1]["price_try"], 57199.0)

    def test_limit(self):
        self.assertEqual(len(P.parse_search_results(self.html, limit=2)), 2)

    def test_empty_html(self):
        self.assertEqual(P.parse_search_results("<html></html>"), [])

    def test_price_stats(self):
        rows = P.parse_search_results(self.html, limit=10)
        stats = P.price_stats(rows)
        self.assertEqual(stats["count"], 10)
        self.assertEqual(stats["min_try"], 57199.0)
        self.assertEqual(stats["median_try"], 106099.49)
        self.assertEqual(stats["mean_try"], 100880.09)
        self.assertEqual(stats["max_try"], 150999.55)

    def test_price_stats_empty(self):
        self.assertEqual(P.price_stats([]), {"count": 0})


class TestDetailParse(unittest.TestCase):
    def setUp(self):
        self.html = _read("product-iphone17.html")

    def test_core_fields(self):
        d = P.parse_product_detail(self.html)
        self.assertEqual(
            d["name"],
            "Apple iPhone 17 Pro Max 256 GB (Apple Türkiye Garantili) "
            "Turuncu 256 GB Fiyatları ve Özellikleri",
        )
        self.assertEqual(d["sku"], "127340433485")
        self.assertEqual(d["brand"], "Apple")
        self.assertEqual(d["price_try"], 112434.28)
        self.assertEqual(d["original_price_try"], 117119.04)
        self.assertEqual(d["price_currency"], "TRY")
        self.assertTrue(d["in_stock"])
        self.assertEqual(d["rating"], 5.0)
        self.assertEqual(d["review_count"], 227)

    def test_category(self):
        d = P.parse_product_detail(self.html)
        self.assertEqual(
            d["category"],
            "Elektronik > Telefon & Aksesuarları > Cep Telefonu > Apple Cep Telefonu",
        )

    def test_seller(self):
        d = P.parse_product_detail(self.html)
        self.assertEqual(d["seller_company"], "SALİM TEKEMEN")
        self.assertEqual(d["seller"], "TKMNBILISIM")
        self.assertEqual(d["seller_badge"], "Yetkili Mağaza")
        self.assertEqual(d["seller_grade"], 100)
        self.assertEqual(d["shipment_city"], "Antalya")
        self.assertEqual(d["shipment_condition"], "Ücretsiz Kargo")

    def test_images(self):
        d = P.parse_product_detail(self.html)
        self.assertEqual(len(d["images"]), 1)
        self.assertTrue(d["images"][0].startswith("https://n11scdn2-im.akamaized.net/"))

    def test_no_product_raises(self):
        with self.assertRaises(ValueError):
            P.parse_product_detail("<html><body>no json-ld here</body></html>")


class TestReviewsParse(unittest.TestCase):
    def test_reviews(self):
        reviews = P.parse_reviews(_read("product-iphone17.html"), limit=5)
        self.assertEqual(len(reviews), 3)
        self.assertEqual(reviews[0]["author"], "Ö*** K***")
        self.assertEqual(reviews[0]["rating"], 5.0)

    def test_limit(self):
        html = _read("product-iphone17.html")
        self.assertEqual(len(P.parse_reviews(html, limit=1)), 1)

    def test_no_reviews(self):
        self.assertEqual(P.parse_reviews("<html></html>"), [])


class TestCategoriesParse(unittest.TestCase):
    def test_eleven_categories(self):
        cats = P.parse_categories(_read("home-categories.html"))
        self.assertEqual(len(cats), 11)
        self.assertEqual(cats[0]["name"], "Moda")
        self.assertEqual(cats[0]["url"], "https://www.n11.com/giyim-ayakkabi")
        self.assertEqual(cats[0]["slug"], "giyim-ayakkabi")
        self.assertEqual(cats[1]["name"], "Elektronik")
        self.assertEqual(cats[-1]["name"], "Yapı Market")

    def test_empty(self):
        self.assertEqual(P.parse_categories("<html></html>"), [])


class TestSorts(unittest.TestCase):
    def test_resolve(self):
        self.assertIsNone(P.resolve_sort("relevance"))
        self.assertEqual(P.resolve_sort("price_asc"), "PRICE_LOW")
        self.assertEqual(P.resolve_sort("price_desc"), "PRICE_HIGH")

    def test_unknown_sort(self):
        with self.assertRaises(ValueError):
            P.resolve_sort("bogus")


class TestServerToolsRegistered(unittest.TestCase):
    def test_five_tools(self):
        from n11_mcp.server import mcp

        tools = asyncio.run(mcp.list_tools())
        names = sorted(t.name for t in tools)
        self.assertEqual(
            names,
            [
                "n11_list_categories",
                "n11_price_stats",
                "n11_product_detail",
                "n11_product_reviews",
                "n11_search",
            ],
        )


if __name__ == "__main__":
    unittest.main()

# n11-mcp 🇹🇷

> ⚠️ **Durum: KISMEN BOZUK (2026-11-10)** — n11.com'un bot duvarı arama yolunu (/arama) zaman zaman engelliyor (yaklaşık 3 aramada 1 başarılı; parmak izi dönüşü ana sayfayı kurtardı). Ana sayfa, kategoriler ve sağlık kontrolü güvenilir çalışıyor. Arama ve fiyat araçları "engellendi — daha sonra tekrar deneyin" hatası verebilir; tekrar denemek bazen işe yarar. Canlı durum için `n11_health` kullanın.


mcp-name: io.github.mohammad-abbasi-sh/n11-mcp

Türkiye'nin 3 numaralı pazaryeri **n11.com** için resmi olmayan,
**salt okunur** MCP sunucusu — milyonlarca üründe arama yapın, ürün
detaylarını okuyun (fiyat, liste fiyatı, stok, puan, satıcı, kategori),
müşteri yorumlarını okuyun, 11 ana kategoriye göz atın ve herhangi bir
sorgu için fiyat istatistikleri (min / medyan / ortalama / maks) alın.

> Mohammad Abbasi tarafından "Turkey MCP factory" (Sepehr tarzı süreç)
> kapsamında geliştirildi. n11.com ile bağlantısı yoktur.

## Yapay zekâ ajanları için

MCP istemci yapılandırmanıza ekleyin (stdio):

```json
{
  "mcpServers": {
    "n11": {
      "command": "uvx",
      "args": ["n11-mcp==0.1.0"]
    }
  }
}
```

veya yerel çalıştırın: `python -m n11_mcp.server`
(`mcp<2`, `curl-cffi` gerekir).

## Araçlar

| Araç | Açıklama |
|------|----------|
| `n11_search` | Anahtar kelimeyle ürün arama — `query` ("iphone", "kablosuz kulaklık"), `sort` ("relevance" / "price_asc" / "price_desc"), `limit` 1..24, `page` 1'den başlar; başlık, TL fiyat, liste fiyatı, marka, SKU, URL, görsel, stok durumu döndürür |
| `n11_product_detail` | Bir ürünün detayı (`product` = "/urun/…" içeren URL veya yol): ad, marka, TL fiyat, liste fiyatı, stok durumu, puan, yorum sayısı, satıcı (şirket, mağaza adı, yetkili mağaza rozeti, satıcı puanı, gönderim şehri), kategori yolu, açıklama, görseller |
| `n11_list_categories` | 11 ana kategori: Türkçe ad, URL, slug |
| `n11_price_stats` | Bir sorgunun fiyat istatistikleri: adet, min / medyan / ortalama / maks fiyat (TL) |
| `n11_product_reviews` | Bir ürünün son müşteri yorumları: yorumcu ve yıldız puanı (n11 yorum metinlerini sunucu taraflı işlemez) |

Örnek çıktı (`n11_search` / "iphone"):

```json
{"query": "iphone", "count": 10, "products": [
  {"title": "Apple iPhone 17 Pro Max 256 GB (Apple Türkiye Garantili)",
   "url": "https://www.n11.com/urun/apple-iphone-17-pro-max-256-gb-apple-turkiye-garantili-100816929",
   "sku": "127340433485", "brand": "Apple", "price_try": 112434.28,
   "original_price_try": 117119.04, "in_stock": true}, …]}
```

## Nasıl çalışır?

n11.com düz HTTP istemcilerine yanıt verir; aktarım yine de Chrome TLS
taklidi (`curl-cffi`, `chrome120`) kullanır, böylece daha katı bir bot
kontrolü sunucuyu bozmaz. Herkese açık bir JSON API yoktur — veriler
sitenin sunucu taraflı işlenmiş HTML sayfalarından gelir: arama
sayfaları schema.org ItemList JSON-LD bloğu (sayfa başına 20 ürün),
ürün sayfaları schema.org Product JSON-LD + breadcrumb kategori yolu +
gömülü satıcı JSON nesnesi, ana sayfa ise 11 ana kategoriyi taşır.
İstekler ~0.8 sn arayla yapılır; her şey salt okunurdur, giriş
gerekmez, API anahtarı gerekmez.

## Kurulum

```bash
uvx n11-mcp==0.1.0        # doğrudan çalıştır (uv gerekir)
# veya
pip install n11-mcp==0.1.0
n11-mcp            # MCP sunucusunu stdio üzerinde başlatır
```

## Testler

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Çevrimdışı testler kayıtlı örnek sayfalarla çalışır (gerçek sayfalar,
2026-11-06); canlı testler n11.com'a bağlanır.

## Lisans

MIT — bkz. [LICENSE](LICENSE).

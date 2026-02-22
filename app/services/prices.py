import httpx
import xml.etree.ElementTree as ET
import asyncio
from typing import Dict, Any

TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"

async def fetch_prices_async() -> Dict[str, Any]:
    """
    TCMB'den döviz kurlarını çeker ve altın fiyatını hesaplar.
    Gelecekte buraya gerçek zamanlı altın API'leri entegre edilebilir.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(TCMB_URL, timeout=10.0)
            resp.raise_for_status()
            
        root = ET.fromstring(resp.content)
        prices = {}
        
        for currency in root.findall("Currency"):
            code = currency.get("CurrencyCode")
            buy = currency.find("ForexBuying")
            sell = currency.find("ForexSelling")

            try:
                buy_val = float(buy.text.replace(",", ".")) if buy is not None and buy.text else None
                sell_val = float(sell.text.replace(",", ".")) if sell is not None and sell.text else None
            except Exception:
                buy_val, sell_val = None, None

            prices[code] = {"buy": buy_val, "sell": sell_val}

        # Altın Fiyatı Hesaplama (Ons üzerinden simüle, 
        # gerçekte bir altın API'sinden çekilmeli)
        # Mevcut ons fiyatını varsayalım (Örn: 2750 USD)
        current_ons_usd = 2750.00 
        
        if "USD" in prices and prices["USD"]["sell"]:
            usd_try = prices["USD"]["sell"]
            # 1 Ons = 31.1034768 gram
            gram_has_gold = (current_ons_usd * usd_try) / 31.1034768
            
            # Farklı altın türleri için hesaplamalar
            prices["GA"] = { # Gram Altın (24 Ayar)
                "buy": round(gram_has_gold * 0.995, 2), # %0.5 makas
                "sell": round(gram_has_gold * 1.005, 2)
            }
            prices["C22"] = { # 22 Ayar Bilezik (0.916 saflık)
                "buy": round(gram_has_gold * 0.916 * 0.98, 2),
                "sell": round(gram_has_gold * 0.916 * 1.02, 2)
            }
            prices["C14"] = { # 14 Ayar (0.585 saflık)
                "buy": round(gram_has_gold * 0.585 * 0.97, 2),
                "sell": round(gram_has_gold * 0.585 * 1.05, 2)
            }

        return prices

    except Exception as e:
        print(f"Error fetching prices: {e}")
        # Fallback (Hata durumunda son fiyatlar veya sabitler)
        return {
            "USD": {"buy": 34.0, "sell": 34.5},
            "EUR": {"buy": 37.0, "sell": 37.5},
            "GA": {"buy": 3000.0, "sell": 3050.0}
        }

# Senkron wrapper (Geriye dönük uyumluluk için)
def fetch_prices():
    return asyncio.run(fetch_prices_async())
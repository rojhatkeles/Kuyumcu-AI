from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import sys
import os

# Paket yapısını desteklemek için dizin ayarı
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.database import Base, engine, get_db
    from app import models, schemas
    from app.services.prices import fetch_prices_async
except ImportError:
    from database import Base, engine, get_db
    import models, schemas
    from services.prices import fetch_prices_async


Base.metadata.create_all(bind=engine)
app = FastAPI(title="Kuyumcu Pro Personalized AI", version="8.3.0")

# --- SETTINGS / MARGINS ---
@app.get("/settings/margins")
def get_margins(db: Session = Depends(get_db)):
    return db.query(models.Margin).all()

@app.post("/settings/margins")
def update_margin(symbol: str, buy_margin: float, sell_margin: float, db: Session = Depends(get_db)):
    db_m = db.query(models.Margin).filter(models.Margin.symbol == symbol).first()
    if not db_m:
        db_m = models.Margin(symbol=symbol)
        db.add(db_m)
    db_m.buy_margin = buy_margin
    db_m.sell_margin = sell_margin
    db.commit()
    return {"status": "ok"}

# --- VAULT / STOCK MANAGEMENT ---
@app.get("/vault")
def get_vault(db: Session = Depends(get_db)):
    """Dükkanın net varlıklarını döner"""
    return db.query(models.Vault).all()

@app.post("/vault/update")
def update_vault(symbol: str, amount: float, db: Session = Depends(get_db)):
    """Açılış stoğu veya sayım düzeltmesi için dükkan varlığını günceller"""
    v = db.query(models.Vault).filter(models.Vault.symbol == symbol).first()
    if not v:
        v = models.Vault(symbol=symbol)
        db.add(v)
    v.balance = amount
    db.commit()
    return v

# --- PRICE ENGINE ---
@app.get("/prices/smart")
async def get_smart_prices(db: Session = Depends(get_db)):
    try:
        live = await fetch_prices_async()
        margins = {m.symbol: m for m in db.query(models.Margin).all()}
        res = {}
        for sym in ["GA", "C22", "USD", "EUR"]:
            d = live.get(sym, {"buy": 0, "sell": 0})
            m = margins.get(sym)
            bm = (m.buy_margin or 0.0) if m else 0.0
            sm = (m.sell_margin or 0.0) if m else 0.0
            l_buy, l_sell = (d.get("buy") or 0.0), (d.get("sell") or 0.0)
            res[sym] = {"suggested_buy": round(l_buy - bm, 2), "suggested_sell": round(l_sell + sm, 2)}
        return res
    except Exception:
        return {"GA": {"suggested_buy": 0, "suggested_sell": 0}}

# --- AI ENGINE ---
@app.get("/ai/suggestions")
async def get_ai_suggestions(db: Session = Depends(get_db)):
    """Kullanıcının SON 15 işlemini analiz ederek alışkanlığını yakalar (Stabil Versiyon)"""
    try:
        live = await fetch_prices_async()
        # Hafızayı tekrar 15 işleme çıkardık
        txs = db.query(models.Transaction).order_by(models.Transaction.ts.desc()).limit(15).all()
        margins = {m.symbol: m for m in db.query(models.Margin).all()}
        
        stats = {}
        for tx in txs:
            if tx.side == "initial": continue
            sym = tx.symbol or "GA"
            if sym not in stats: stats[sym] = {"sell": [], "buy": []}
            m = live.get(sym, live.get("GA", {"buy":0}))
            ref = m.get("buy") or 0
            if tx.side == "sell": stats[sym]["sell"].append(tx.unit_price - ref)
            else: stats[sym]["buy"].append(ref - tx.unit_price)
        
        sugs = []
        for sym, data in stats.items():
            # Eşik değerini tekrar normale çektik (USD için 0.1, Altın için 1.0)
            threshold = 0.1 if sym in ["USD", "EUR"] else 1.0
            
            if data["sell"]:
                avg_user_margin = sum(data["sell"])/len(data["sell"])
                cur_m = margins.get(sym)
                cur_setting = (cur_m.sell_margin if cur_m else 0) or 0.0
                
                if abs(avg_user_margin - cur_setting) > threshold:
                    sugs.append({
                        "symbol": sym, 
                        "type": "Satış", 
                        "suggested": round(avg_user_margin, 2),
                        "msg": f"{sym} için tarzınız {round(avg_user_margin,2)} TL marja kaymış."
                    })
        return sugs
    except:
        return []

# --- TRANSACTIONS ---
@app.post("/transactions")
def add_tx(tx: schemas.TransactionCreate, db: Session = Depends(get_db)):
    # İşlemi kaydet
    ntx = models.Transaction(**tx.model_dump(), ts=datetime.now())
    db.add(ntx)
    
    # KASAYI GÜNCELLE (Vault)
    # TL Kasası (TRY)
    try_v = db.query(models.Vault).filter(models.Vault.symbol == "TRY").first()
    if not try_v: try_v = models.Vault(symbol="TRY", balance=0.0); db.add(try_v)
    
    # 2. Ürün Stoğunu Güncelle (Eğer ürün seçildiyse)
    if tx.product_id:
        prod = db.get(models.Product, tx.product_id)
        if prod:
            if tx.side == "sell":
                prod.stock_qty -= int(tx.qty)
            elif tx.side == "buy":
                prod.stock_qty += int(tx.qty)



    # 3. Kasa veya Müşteri Bakiyesini Güncelle
    is_debt = (tx.payment_type == "Debt")
    
    # 3A. Müşteri Cari Hesaba Yazma (Veresiye/Açık Hesap)
    if is_debt and tx.customer_id:
        cust = db.get(models.Customer, tx.customer_id)
        if cust:
            # Dükkan satış yapıyorsa müşteri borçlanır (+), alış yapıyorsa müşteri alacaklanır (-)
            multiplier = 1 if tx.side == "sell" else -1
            
            # Altın mı, TL bazlı mı?
            if tx.symbol == "GA":
                cust.balance_gold += (tx.qty * multiplier)
            else:
                cust.balance_try += (tx.total_price * multiplier)
            
            # Ürün dükkandan çıkıyor (veya giriyor), bu yüzden kasa stokları yine güncellenmeli 
            # ancak TL kasasına nakit giriş/çıkış olmaz, sadece stok (altın/ürün vb) güncellenir.
            if tx.symbol and tx.symbol != "ÜRÜN" and tx.symbol != "TRY":
                sym_v = db.query(models.Vault).filter(models.Vault.symbol == tx.symbol).first()
                if not sym_v: sym_v = models.Vault(symbol=tx.symbol, balance=0.0); db.add(sym_v)
                sym_v.balance += (tx.qty * (-multiplier)) # Dükkan: Satışsa eksi, alışsa artı
                
    # 3B. Nakit İşlem (Peşin/Kredi Kartı - Direk Kasaya İşle)
    else:
        if tx.symbol and tx.symbol != "ÜRÜN":
            sym_v = db.query(models.Vault).filter(models.Vault.symbol == tx.symbol).first()
            if not sym_v: sym_v = models.Vault(symbol=tx.symbol, balance=0.0); db.add(sym_v)
            
            if tx.side == "sell":
                try_v.balance += tx.total_price
                sym_v.balance -= tx.qty
            elif tx.side == "buy":
                try_v.balance -= tx.total_price
                sym_v.balance += tx.qty
        elif tx.symbol == "ÜRÜN" and tx.side == "sell":
            try_v.balance += tx.total_price
        elif tx.symbol == "ÜRÜN" and tx.side == "buy":
            try_v.balance -= tx.total_price

    db.commit()
    return ntx



@app.get("/transactions")
def list_tx(db: Session = Depends(get_db)):
    return db.query(models.Transaction).order_by(models.Transaction.ts.desc()).all()

# --- REPORTS (MULTİ-CASH VALUATION) ---
@app.get("/reports/kasa")
async def get_kasa(db: Session = Depends(get_db)):
    # 1. Kasadaki Hammaddeler (Naklit, USD, Has Altın)
    v_data = {v.symbol: v.balance for v in db.query(models.Vault).all()}
    
    # 2. Stoktaki İşlenmiş Ürünler (Künye, Bilezik vb)
    products = db.query(models.Product).filter(models.Product.stock_qty > 0).all()
    total_product_weight = sum(p.weight * p.purity * p.stock_qty for p in products) # Has Altın Karşılığı
    total_labor_tl = sum(p.labor_cost * p.stock_qty for p in products)
    
    live = await fetch_prices_async()
    
    # 3. Toplam TL Değerini Bulalım (Kasalar + Ürünlerin Has Değeri + İşçilikler)
    total_tl = v_data.get("TRY", 0.0) + total_labor_tl
    for sym in ["GA", "USD", "EUR"]:
        price = live.get(sym, {"buy": 0})["buy"]
        total_tl += v_data.get(sym, 0.0) * price
    
    # Ürünlerin has ağırlığını da GA kasasına eklemiş gibi değerleyelim
    p_ga = live.get("GA", {"buy": 1})["buy"] or 1
    total_tl += total_product_weight * p_ga
        
    # 4. Diğer Birimlere Çevrim
    p_usd = live.get("USD", {"buy": 1})["buy"] or 1
    p_eur = live.get("EUR", {"buy": 1})["buy"] or 1
    
    return {
        "balances": v_data,
        "product_stock": {
            "total_weight_has": round(total_product_weight, 3),
            "total_labor_tl": round(total_labor_tl, 2)
        },
        "total_gold_has": round(v_data.get("GA", 0.0) + total_product_weight, 3),
        "valuation": {
            "TRY": round(total_tl, 2),
            "USD": round(total_tl / p_usd, 2),
            "EUR": round(total_tl / p_eur, 2),
            "GA": round(total_tl / p_ga, 3)
        }
    }




@app.get("/reports/pnl")
async def get_pnl(db: Session = Depends(get_db)):
    txs, cur = db.query(models.Transaction).all(), await fetch_prices_async()
    total = 0.0
    for t in txs:
        m = cur.get(t.symbol or "GA", cur.get("GA", {"buy":0}))
        ref = m.get("buy") or 0
        if t.side == "sell": total += (t.unit_price - ref) * t.qty
        else: total += (ref - t.unit_price) * t.qty
    return {"profit": round(total, 2)}

@app.get("/reports/analytics")
def get_analytics(db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)
    txs = db.query(models.Transaction).filter(models.Transaction.ts >= thirty_days_ago).all()
    
    total_buy = sum(t.total_price for t in txs if t.side == "buy" and t.total_price)
    total_sell = sum(t.total_price for t in txs if t.side == "sell" and t.total_price)
    
    category_sales = {}
    symbol_sales = {}
    for t in txs:
        if t.side == "sell":
            if t.product_id:
                prod = db.get(models.Product, t.product_id)
                cat = prod.category if prod and prod.category else "Ürün"
                category_sales[cat] = category_sales.get(cat, 0) + (t.total_price or 0)
            elif t.symbol and t.symbol != "ÜRÜN":
                symbol_sales[t.symbol] = symbol_sales.get(t.symbol, 0) + (t.total_price or 0)

    category_keys = list(category_sales.keys())
    category_values = list(category_sales.values())

    symbol_keys = list(symbol_sales.keys())
    symbol_values = list(symbol_sales.values())

    return {
        "volume": {"buy": round(total_buy, 2), "sell": round(total_sell, 2)},
        "category_sales": {"labels": category_keys, "values": category_values},
        "symbol_sales": {"labels": symbol_keys, "values": symbol_values}
    }

# --- PRODUCTS ---
@app.get("/products")
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).filter(models.Product.stock_qty > 0).all()


@app.post("/products")
def create_product(p: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_p = models.Product(**p.model_dump())
    db.add(db_p); db.commit(); db.refresh(db_p); return db_p

# --- CUSTOMERS ---
@app.get("/customers")
def list_customers(db: Session = Depends(get_db)):
    return db.query(models.Customer).all()

@app.post("/customers")
def create_customer(c: schemas.CustomerCreate, db: Session = Depends(get_db)):
    db_c = models.Customer(**c.model_dump())
    db.add(db_c); db.commit(); db.refresh(db_c); return db_c

@app.post("/customers/{customer_id}/payment")
def process_customer_payment(customer_id: int, amount: float, p_type: str, db: Session = Depends(get_db)):
    # p_type: "tahsilat" (müşteri öder, kasaya girer, borç düşer), "odeme" (biz öderiz, kasadan çıkar, borç artar)
    cust = db.get(models.Customer, customer_id)
    if not cust: return {"error": "Müşteri bulunamadı"}
    
    try_v = db.query(models.Vault).filter(models.Vault.symbol == "TRY").first()
    if not try_v: try_v = models.Vault(symbol="TRY", balance=0.0); db.add(try_v)

    if p_type == "tahsilat":
        cust.balance_try -= amount  # Müşterinin bize borcu azalır (veya bizim ona borcumuz artar)
        try_v.balance += amount     # Kasamıza para girer
    elif p_type == "odeme":
        cust.balance_try += amount  # Müşteriye para verdik, borcu arttı
        try_v.balance -= amount     # Kasamızdan para çıktı
        
    db.commit()
    return {"message": "İşlem başarılı", "new_balance": cust.balance_try}


@app.get("/prices")
async def get_prices():
    return await fetch_prices_async()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


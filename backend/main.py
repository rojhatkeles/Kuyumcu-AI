from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import sys
import os
import hashlib


# Paket yapısını desteklemek için dizin ayarı
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.database import Base, engine, get_db, SessionLocal
    from backend import models, schemas
    from backend.services.prices import fetch_prices_async
except ImportError:
    from database import Base, engine, get_db, SessionLocal
    import models, schemas
    from services.prices import fetch_prices_async


# --- LICENSE SETTINGS ---
LICENSE_TIER = "NORMAL"

# --- MIDDLEWARE / UTILS ---
def check_premium():
    if LICENSE_TIER != "PREMIUM":
        raise HTTPException(status_code=402, detail="Bu özellik sadece Kuyumcu Pro Premium üyeleri içindir.")
    return True


def refresh_license_tier():
    global LICENSE_TIER
    db = SessionLocal()
    try:
        # DB'deki tier'ı al
        cfg = db.query(models.Config).filter(models.Config.key == "license_tier").first()
        if not cfg:
            cfg = models.Config(key="license_tier", value="NORMAL")
            db.add(cfg); db.commit()
            LICENSE_TIER = "NORMAL"
            return

        current_tier = cfg.value
        
        # Eğer Premium ise key'i doğrula
        if current_tier == "PREMIUM":
            key_cfg = db.query(models.Config).filter(models.Config.key == "license_key").first()
            if not key_cfg or not key_cfg.value:
                cfg.value = "NORMAL"
                db.commit()
                LICENSE_TIER = "NORMAL"
            else:
                # Key var, ama gerçekten geçerli mi? (Offline güven modu: PRO- ile başlamalı)
                if not key_cfg.value.startswith("PRO-"):
                    cfg.value = "NORMAL"
                    db.commit()
                    LICENSE_TIER = "NORMAL"
                else:
                    LICENSE_TIER = "PREMIUM"
        else:
            LICENSE_TIER = "NORMAL"
            
    except Exception as e:
        print(f"License check error: {e}")
        LICENSE_TIER = "NORMAL"
    finally:
        db.close()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Test ortamında gerçek DB'yi init etme (Deadlock'ı önle)
    if not os.getenv("TESTING"):
        Base.metadata.create_all(bind=engine)
        refresh_license_tier()
    yield

app = FastAPI(title="Kuyumcu Pro Personalized AI", version="8.3.0", lifespan=lifespan)


@app.get("/system/tier")
def get_tier():
    return {"tier": LICENSE_TIER}

@app.post("/system/activate")
def activate_system(req: schemas.ActivationRequest, db: Session = Depends(get_db)):
    global LICENSE_TIER
    import requests
    # WEB SUNUCUSUNA (localhost:8080) SORUYORUZ
    try:
        r = requests.get(f"http://127.0.0.1:8080/api/license/verify?key={req.license_key}", timeout=2)
        if r.status_code == 200:
            cfg = db.query(models.Config).filter(models.Config.key == "license_tier").first()
            if not cfg:
                cfg = models.Config(key="license_tier")
                db.add(cfg)
            cfg.value = "PREMIUM"
            
            key_cfg = db.query(models.Config).filter(models.Config.key == "license_key").first()
            if not key_cfg:
                key_cfg = models.Config(key="license_key")
                db.add(key_cfg)
            key_cfg.value = req.license_key
            db.commit()
            LICENSE_TIER = "PREMIUM"
            return {"status": "ok", "message": "Lisans doğrulandı! Premium aktif."}
        else:
            raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş lisans anahtarı.")
    except HTTPException:
        raise
    except Exception as e:
        # Web sunucusu kapalıysa bile localdeki kurala bakabiliriz (Geriye dönük uyumluluk)
        if req.license_key.startswith("PRO-"):
            cfg = db.query(models.Config).filter(models.Config.key == "license_tier").first()
            if not cfg:
                cfg = models.Config(key="license_tier")
                db.add(cfg)
            cfg.value = "PREMIUM"
            
            key_cfg = db.query(models.Config).filter(models.Config.key == "license_key").first()
            if not key_cfg:
                key_cfg = models.Config(key="license_key")
                db.add(key_cfg)
            key_cfg.value = req.license_key
            db.commit()
            
            LICENSE_TIER = "PREMIUM"
            return {"status": "ok", "message": "Offline doğrulama başarılı! Premium aktif."}
        raise HTTPException(status_code=500, detail=f"Lisans sunucusuna bağlanılamadı: {e}")

@app.post("/system/sync")
async def cloud_sync(premium: bool = Depends(check_premium), db: Session = Depends(get_db)):
    """Dükkan verilerini Bulut (Web) sunucusuna gönderir"""
    key_cfg = db.query(models.Config).filter(models.Config.key == "license_key").first()
    if not key_cfg:
        raise HTTPException(status_code=403, detail="Lisans anahtarı bulunamadı.")
    
    # Kasa ve Rapor verilerini topla (Aynı dosyadaki fonksiyonları çağırıyoruz)
    kasa = await get_kasa(db)
    daily = await get_daily(db)
    
    payload = {
        "kasa": kasa,
        "daily_profit": daily["profit"],
        "tx_count": len(daily["transactions"])
    }
    
    import requests
    try:
        r = requests.post(f"http://127.0.0.1:8080/api/sync/report?key={key_cfg.value}", json=payload, timeout=5)
        if r.status_code == 200:
            return r.json()
        else:
            raise HTTPException(status_code=r.status_code, detail="Web merkezi hata döndürdü.")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Web merkezine ulaşılamadı (8080 kapalı olabilir): {e}")

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
    allowed = ["TRY", "USD", "EUR", "GA", "C22", "CEYREK", "YARIM", "TAM", "ATA"]
    if symbol not in allowed:
        raise HTTPException(status_code=400, detail=f"Geçersiz sembol: {symbol}")

    v = db.query(models.Vault).filter(models.Vault.symbol == symbol).first()
    if not v:
        v = models.Vault(symbol=symbol, balance=0.0)
        db.add(v)
    v.balance = (v.balance or 0.0) + amount
    db.commit()
    return {"status": "ok", "new_balance": v.balance}


# --- PRICE ENGINE ---
@app.get("/prices/smart")
async def get_smart_prices(db: Session = Depends(get_db)):
    try:
        live = await fetch_prices_async()
        margins = {m.symbol: m for m in db.query(models.Margin).all()}
        res = {}
        for sym in live.keys():
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
async def get_ai_suggestions(premium: bool = Depends(check_premium), db: Session = Depends(get_db)):
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
    query = db.query(models.Transaction)
    
    if LICENSE_TIER == "NORMAL":
        seven_days_ago = datetime.now() - timedelta(days=7)
        query = query.filter(models.Transaction.ts >= seven_days_ago)
        
    return query.order_by(models.Transaction.ts.desc()).all()

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
async def get_pnl(premium: bool = Depends(check_premium), db: Session = Depends(get_db)):
    txs, cur = db.query(models.Transaction).all(), await fetch_prices_async()
    total = 0.0
    for t in txs:
        m = cur.get(t.symbol or "GA", cur.get("GA", {"buy":0}))
        ref = m.get("buy") or 0
        if t.side == "sell": total += (t.unit_price - ref) * t.qty
        else: total += (ref - t.unit_price) * t.qty
    return {"profit": round(total, 2)}

@app.get("/reports/daily")
async def get_daily(db: Session = Depends(get_db)):
    from datetime import date
    
    # Bugünün işlemleri (Transaction modelinde ts DateTime tipinde olduğu için bugüne göre filtreleyeceğiz)
    today_start = date.today().isoformat()
    # Tüm işlemleri çekip bellekte bugünün tarihini filtreleyelim 
    # (Daha verimli yöntem veri tabanı filtredir ancak sqlite ile safe olmak için string startswith yapabiliriz)
    txs_all = db.query(models.Transaction).order_by(models.Transaction.ts.desc()).all()
    txs = [t for t in txs_all if t.ts and str(t.ts).startswith(today_start)]
    
    cur = await fetch_prices_async()
    daily_profit = 0.0
    daily_txs = []
    
    for t in txs:
        # Kar/Zarar Hesaplaması
        m = cur.get(t.symbol or "GA", cur.get("GA", {"buy":0}))
        ref = m.get("buy") or 0
        if t.side == "sell": daily_profit += (t.unit_price - ref) * t.qty
        else: daily_profit += (ref - t.unit_price) * t.qty
        
        # Gösterim için işlem objesi
        daily_txs.append({
            "ts": t.ts.split("T")[1][:5] if "T" in str(t.ts) else str(t.ts).split(" ")[1][:5] if " " in str(t.ts) else str(t.ts),
            "side": "SATIŞ" if t.side == "sell" else "ALIŞ",
            "symbol": t.symbol,
            "qty": t.qty,
            "unit_price": t.unit_price,
            "total_price": t.total_price,
            "payment_type": t.payment_type
        })
        
    return {
        "profit": round(daily_profit, 2),
        "transactions": daily_txs
    }

@app.get("/reports/analytics")
def get_analytics(premium: bool = Depends(check_premium), db: Session = Depends(get_db)):
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
    if LICENSE_TIER == "NORMAL":
        count = db.query(models.Customer).count()
        if count >= 20:
            raise HTTPException(status_code=402, detail="Cari Limitiniz Doldu (20/20). Sınırsız müşteri kaydı için Kuyumcu Pro Premium'a geçin.")
            
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

# --- USERS / AUTH ---
def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.post("/users", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if LICENSE_TIER == "NORMAL":
        count = db.query(models.User).count()
        if count >= 1:
            raise HTTPException(status_code=402, detail="Normal pakette sadece 1 Admin hesabı kullanılabilir. Çoklu personel desteği için Premium lisansa geçin.")

    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        password=hashed_password,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if db_user.password != get_password_hash(user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    return {"message": "Login successful", "user": {"id": db_user.id, "username": db_user.username, "role": db_user.role}}

@app.get("/users/ensure_admin")
def ensure_admin(db: Session = Depends(get_db)):
    # Create default admin if not exists
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        new_admin = models.User(
            username="admin",
            password=get_password_hash("admin123"),
            role="admin"
        )
        db.add(new_admin)
        db.commit()
        return {"message": "Default admin created (admin123)"}
    return {"message": "Admin exists"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

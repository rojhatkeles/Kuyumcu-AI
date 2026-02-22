from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from .database import Base, engine, get_db
from . import models, schemas
from .services.prices import fetch_prices_async

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Kuyumcu Pro Personal AI", version="8.1.0")

@app.get("/prices/smart")
async def get_smart_prices(db: Session = Depends(get_db)):
    """Canlı fiyatlara marjları ekleyerek önerilen fiyatları döner"""
    try:
        live = await fetch_prices_async()
        margins = {m.symbol: m for m in db.query(models.Margin).all()}
        res = {}
        # Temel sembollerin olduğundan emin olalım
        for sym in ["GA", "C22", "USD", "EUR"]:
            d = live.get(sym, {"buy": 0, "sell": 0})
            m = margins.get(sym)
            bm = (m.buy_margin or 0.0) if m else 0.0
            sm = (m.sell_margin or 0.0) if m else 0.0
            
            # Null güvenliği
            l_buy = d.get("buy") or 0.0
            l_sell = d.get("sell") or 0.0
            
            res[sym] = {
                "suggested_buy": round(l_buy - bm, 2),
                "suggested_sell": round(l_sell + sm, 2)
            }
        return res
    except Exception as e:
        print(f"Smart Price Error: {e}")
        return {"GA": {"suggested_buy": 0, "suggested_sell": 0}}

@app.get("/ai/suggestions")
async def get_ai_suggestions(db: Session = Depends(get_db)):
    live = await fetch_prices_async()
    txs = db.query(models.Transaction).order_by(models.Transaction.ts.desc()).limit(50).all()
    margins = {m.symbol: m for m in db.query(models.Margin).all()}
    stats = {}
    for tx in txs:
        sym = tx.symbol or "GA"
        if sym not in stats: stats[sym] = {"sell": [], "buy": []}
        m = live.get(sym, live.get("GA", {"buy":0}))
        ref = m.get("buy") or 0
        if tx.side == "sell": stats[sym]["sell"].append(tx.unit_price - ref)
        else: stats[sym]["buy"].append(ref - tx.unit_price)
    
    sugs = []
    for sym, data in stats.items():
        if not (data["sell"] or data["buy"]): continue
        if data["sell"]:
            avg = sum(data["sell"])/len(data["sell"])
            cur = (margins.get(sym).sell_margin if margins.get(sym) else 0)
            if abs(avg - cur) > 1.0:
                sugs.append({"symbol": sym, "type": "Satış", "current": round(cur, 2), "suggested": round(avg, 2)})
    return sugs

# Standartlar
@app.post("/settings/margins")
def update_margin(symbol: str, buy_margin: float, sell_margin: float, db: Session = Depends(get_db)):
    db_m = db.query(models.Margin).filter(models.Margin.symbol == symbol).first()
    if not db_m: db_m = models.Margin(symbol=symbol); db.add(db_m)
    db_m.buy_margin, db_m.sell_margin = buy_margin, sell_margin; db.commit(); return {"status": "ok"}
@app.post("/transactions")
def add_tx(tx: schemas.TransactionCreate, db: Session = Depends(get_db)):
    ntx = models.Transaction(**tx.model_dump(), ts=datetime.now()); db.add(ntx); db.commit(); return ntx
@app.get("/reports/kasa")
async def get_kasa(db: Session = Depends(get_db)):
    txs = db.query(models.Transaction).all(); c, g = 1000000.0, 0.0
    for t in txs:
        if t.side == "sell": c += t.total_price; g -= (t.qty or 0)
        else: c -= t.total_price; g += (t.qty or 0)
    return {"current_cash_tl": round(c, 2), "current_gold_stock": round(g, 3)}
@app.get("/reports/pnl")
async def get_pnl(db: Session = Depends(get_db)):
    txs, cur = db.query(models.Transaction).all(), await fetch_prices_async()
    total = sum((t.unit_price - cur.get(t.symbol or "GA", cur["GA"])["buy"]) * t.qty if t.side == "sell" else (cur.get(t.symbol or "GA", cur["GA"])["buy"] - t.unit_price) * t.qty for t in txs)
    return {"profit": round(total, 2)}
@app.get("/transactions")
def get_txs(db: Session = Depends(get_db)): return db.query(models.Transaction).order_by(models.Transaction.ts.desc()).all()
@app.get("/prices")
async def get_pr(): return await fetch_prices_async()
@app.get("/products")
def list_p(db: Session = Depends(get_db)): return db.query(models.Product).all()
@app.get("/customers")
def list_c(db: Session = Depends(get_db)): return db.query(models.Customer).all()

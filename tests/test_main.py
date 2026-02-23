import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
import warnings
import sys, os


# Add root project path to sys.path so pytest can find 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Uygulama modüllerini içe aktar
from app.main import app, get_db

from app.database import Base
from app import models, schemas

# Testler için bellekte geçici bir veritabanı oluşturalım (SQLite In-Memory)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Endpoint'lerdeki veritabanı bağımlılığını (Depends) geçici veritabanımızla ezelim
# Endpoint'lerdeki veritabanı bağımlılığını (Depends) geçici veritabanımızla ezelim
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Pytest fixture'ı: Her testten önce tabloları sıfırdan oluşturup test bitince siler
@pytest.fixture(autouse=True)
def setup_database():
    # import models to ensure Base has all metadata registered
    from app.database import Base
    from app import models
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# ------------- TEST SENARYOLARI -------------

def test_create_and_list_product():
    """Ürün (Stok) ekleme ve listeleme (Stock > 0 filtreli) testi"""
    prod_data = {
        "name": "Bilezik Test",
        "category": "Bilezik",
        "weight": 20.0,
        "purity": 0.916,
        "labor_cost": 500.0,
        "stock_qty": 2
    }
    
    # Ürünü ekle
    response = client.post("/products", json=prod_data)
    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Bilezik Test"
    assert data["stock_qty"] == 2
    
    # Listele (Stok > 0 olanlar gelmeli)
    response = client.get("/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 1
    assert products[0]["name"] == "Bilezik Test"

def test_customer_creation_and_payment():
    """Müşteri cari hesabı ve manuel tahsilat/ödeme işlemi"""
    # Müşteri yarat
    cust_data = {"full_name": "Ahmet Test", "phone": "5551234567"}
    res = client.post("/customers", json=cust_data)
    assert res.status_code == 200
    cust_id = res.json()["id"]
    
    # Tahsilat yap: Müşteriden 1000 TL aldık (Müşterinin bakiyesi -1000 olmalı)
    res_pay = client.post(f"/customers/{cust_id}/payment", params={"amount": 1000.0, "p_type": "tahsilat"})
    assert res_pay.status_code == 200
    assert res_pay.json()["new_balance"] == -1000.0
    
    # Kasaya bak: 1000 TL girmiş olmalı
    res_vault = client.get("/reports/kasa")
    assert res_vault.status_code == 200
    assert res_vault.json()["balances"].get("TRY", 0) == 1000.0

def test_debt_transaction():
    """Veresiye Satış test: Kasa değişmemeli, ürün stok'tan düşmeli ve müşteri borçlanmalı"""
    # Müşteri ve Ürün ekle
    c_res = client.post("/customers", json={"full_name": "Borçlu Ali", "phone": "1112223344"})
    cust_id = c_res.json()["id"]
    
    p_res = client.post("/products", json={"name": "Tektaş", "category": "Yüzük", "weight": 5.0, "purity": 0.585, "labor_cost": 200, "stock_qty": 1})
    prod_id = p_res.json()["id"]

    
    # Veresiye Satış yap
    tx_data = {
        "side": "sell",
        "qty": 1.0,
        "unit_price": 10000.0,
        "total_price": 10000.0,
        "symbol": "ÜRÜN",
        "customer_id": cust_id,
        "product_id": prod_id,
        "payment_type": "Debt"
    }
    tx_res = client.post("/transactions", json=tx_data)
    assert tx_res.status_code == 200
    
    # Müşteri 10000 TL borçlanmış olmalı
    cust_check = client.get("/customers").json()
    ali = next(c for c in cust_check if c["id"] == cust_id)
    assert ali["balance_try"] == 10000.0
    
    # Ürün stoktan düşülmüş olmalı (sattığımız için stok adedi azaldı, sıfırlandı)
    prods_check = client.get("/products").json()
    assert len(prods_check) == 0  # stock_qty > 0 filtresinden dolayı boş dönmeli



def test_cash_transaction():
    """Peşin Satış test: Kasa TRY artmalı, döviz/altın kasası azalmalı (Veya ürün stok düşmeli)"""
    # Önden Has Altın Kasasına 10 gram ekleyelim
    client.post("/vault/update", params={"symbol": "GA", "amount": 10.0})
    
    # Peşin 1 gram Has Altın satalım
    tx_data = {
        "side": "sell",
        "qty": 1.0,
        "unit_price": 3000.0,
        "total_price": 3000.0,
        "symbol": "GA",
        "payment_type": "Cash"
    }
    tx_res = client.post("/transactions", json=tx_data)
    assert tx_res.status_code == 200
    
    # Kasa Raporunu kontrol edelim: TRY=3000, GA=9.0 olmalı
    rep_res = client.get("/reports/kasa").json()
    bals = rep_res["balances"]
    assert bals.get("TRY", 0) == 3000.0
    assert bals.get("GA", 0) == 9.0

def test_analytics_report():
    """Yeni eklenen Analytics raporunun doğru veri döndürdüğünü test eder"""
    # Önceden sahte bir işlem ekle
    tx_data = {"side": "buy", "qty": 1.0, "unit_price": 4000.0, "total_price": 4000.0, "symbol": "GA", "payment_type": "Cash"}
    client.post("/transactions", json=tx_data)

    res = client.get("/reports/analytics")
    assert res.status_code == 200
    data = res.json()
    assert "volume" in data
    assert "category_sales" in data
    assert "symbol_sales" in data
    assert data["volume"]["buy"] >= 4000.0

def test_ai_suggestions():
    """AI Öneri motorunun hata vermeden yapısal JSON (Öneri listesi) döndürdüğünü test eder"""
    res = client.get("/ai/suggestions")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_debt_payment_gold():
    """Müşterinin Altın tabanlı (GA) veresiye alımını test eder"""
    c_res = client.post("/customers", json={"full_name": "Altın Borçlusu", "phone": "999"})
    cust_id = c_res.json()["id"]

    # Müşteriye 5 gram Has Altın veresiye satıyoruz
    tx_data = {
        "side": "sell",
        "qty": 5.0,
        "unit_price": 3000.0,
        "total_price": 15000.0,
        "symbol": "GA",
        "customer_id": cust_id,
        "payment_type": "Debt"
    }
    client.post("/transactions", json=tx_data)

    # Müşteri verilerini çek ve balance_gold kontrol et
    custs = client.get("/customers").json()
    borclu = next(c for c in custs if c["id"] == cust_id)
    # Satış () -> dükkan altını verir, müşteri borçlanır = +5 gram
    assert borclu["balance_gold"] == 5.0

def test_pnl_report():
    """Kar / Zarar Raporunun başarıyla döndüğünü test eder."""
    res = client.get("/reports/pnl")
    assert res.status_code == 200
    data = res.json()
    assert "profit" in data
    assert isinstance(data["profit"], (int, float))


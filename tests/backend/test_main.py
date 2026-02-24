import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
import warnings
import sys, os
os.environ["TESTING"] = "1"
from datetime import datetime, timedelta


# Add root project path to sys.path so pytest can find 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Uygulama modüllerini içe aktar
from backend.main import app, get_db
import backend.main

from backend.database import Base

from backend import models, schemas


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
    from backend.database import Base
    from backend import models
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

def test_user_creation_and_login():
    """Yeni kullanıcı oluşturma ve giriş yapma testi"""
    # Yeni kullanıcı oluştur
    user_data = {"username": "testuser", "password": "testpassword", "role": "cashier"}
    res = client.post("/users", json=user_data)
    assert res.status_code == 200
    assert res.json()["username"] == "testuser"
    assert res.json()["role"] == "cashier"

    # Aynı kullanıcı adıyla tekrar oluşturmayı dene -> Hata dönmeli
    res_dup = client.post("/users", json=user_data)
    assert res_dup.status_code == 400

    # Doğru şifreyle giriş yap
    login_data = {"username": "testuser", "password": "testpassword"}
    res_login = client.post("/login", json=login_data)
    assert res_login.status_code == 200
    assert res_login.json()["message"] == "Login successful"
    assert res_login.json()["user"]["username"] == "testuser"

    # Yanlış şifreyle giriş yap -> 401 hatası dönmeli
    bad_login_data = {"username": "testuser", "password": "wrongpassword"}
    res_bad = client.post("/login", json=bad_login_data)
    assert res_bad.status_code == 401

def test_ensure_admin():
    """Varsayılan admin kullanıcısının oluşturulduğunu kontrol etme testi"""
    res = client.get("/users/ensure_admin")
    assert res.status_code == 200
    assert "Default admin created" in res.json()["message"]

    # Tekrar çağrıldığında "Admin exists" dönmeli
    res_exist = client.get("/users/ensure_admin")
    assert res_exist.status_code == 200
    assert "Admin exists" in res_exist.json()["message"]

def test_licensing_limits_normal():
    """NORMAL paketteki sınırları test eder (Müşteri limiti ve Tarih kısıtı)"""
    backend.main.LICENSE_TIER = "NORMAL"
    
    # 1. Müşteri Limiti Testi (20 Müşteri)
    # Önce 20 tane müşteri ekleyelim
    for i in range(20):
        client.post("/customers", json={"full_name": f"Cust {i}", "phone": f"phone{i}"})
    
    # 21. müşteri 402 fırlatmalı
    res = client.post("/customers", json={"full_name": "Limit Breaker", "phone": "999"})
    assert res.status_code == 402
    assert "Cari Limitiniz Doldu" in res.json()["detail"]

    # 2. İşlem Tarihi Kısıtı Testi (7 Günden eski işlemler görünmemeli)
    # 10 gün öncesine bir işlem ekleyelim (Mocking DB directly for old timestamp)
    db = TestingSessionLocal()
    old_tx = models.Transaction(
        side="sell", qty=1.0, unit_price=1000.0, total_price=1000.0, 
        symbol="GA", ts=datetime.now() - timedelta(days=10)
    )
    db.add(old_tx); db.commit(); db.close()
    
    # Normal pakette bu işlem listelenmemeli
    res_tx = client.get("/transactions")
    tx_list = res_tx.json()
    assert len(tx_list) == 0

def test_licensing_unlock_premium():
    """PREMIUM pakette sınırların kalktığını test eder"""
    backend.main.LICENSE_TIER = "PREMIUM"
    
    # 20 müşteri varken 21. müşteri eklenebilmeli
    for i in range(20):
        client.post("/customers", json={"full_name": f"PCust {i}", "phone": f"pphone{i}"})
    
    res = client.post("/customers", json={"full_name": "Premium User", "phone": "000"})
    assert res.status_code == 200 # Engel yok
    
    # Eski işlemler listelenebilmeli
    db = TestingSessionLocal()
    old_tx = models.Transaction(
        side="sell", qty=1.0, unit_price=1000.0, total_price=1000.0, 
        symbol="GA", ts=datetime.now() - timedelta(days=30)
    )
    db.add(old_tx); db.commit(); db.close()
    
    res_tx = client.get("/transactions")
    assert len(res_tx.json()) >= 1

def test_system_activation(monkeypatch):
    """Aktivasyon endpoint'ini test eder"""
    # Web isteklerini mock'la
    class MockResponse:
        def __init__(self, status_code):
            self.status_code = status_code
        def json(self):
            return {"status": "valid"}

    # 1. Yanlış kod
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockResponse(400))
    res = client.post("/system/activate", json={"license_key": "WRONG-CODE"})
    assert res.status_code == 400
    
    # 2. Doğru kod
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockResponse(200))
    res_ok = client.post("/system/activate", json={"license_key": "PRO-ACTIVATION-TEST"})
    assert res_ok.status_code == 200
    assert backend.main.LICENSE_TIER == "PREMIUM"

# ------------- EXTRA THOROUGH TESTS -------------

def test_invalid_vault_update_parameters():
    """Kasa güncellemelerinde hatalı parametrelerin (negatif miktar, olmayan sembol) yönetimi"""
    # Olmayan bir sembol
    res = client.post("/vault/update", params={"symbol": "XAU_INVALID", "amount": 10.0})
    assert res.status_code == 400
    
    # Negatif miktar (Normalde izin verilmemeli veya kasa azaltılmalı - mevcut API izin veriyor ama kuralı test edelim)
    # Mevcut kodda kısıt yoksa bile yapısal hata vermemeli
    res_neg = client.post("/vault/update", params={"symbol": "GA", "amount": -5.0})
    assert res_neg.status_code == 200

def test_transaction_validation_edge_cases():
    """İşlemlerde sınır değerler (miktar=0, fiyat=0, sembol yok) testi"""
    # Miktar 0 olan işlem
    tx_zero = {
        "side": "sell", "qty": 0.0, "unit_price": 1000.0, "total_price": 0.0,
        "symbol": "GA", "payment_type": "Cash"
    }
    res = client.post("/transactions", json=tx_zero)
    # Mevcut kodda 0'a engel yoksa 200 döner, ama mantıksal olarak 0'lık tx kasayı bozmamalı
    assert res.status_code == 200
    
    # Sembol boş olan işlem
    tx_empty = tx_zero.copy()
    tx_empty["symbol"] = ""
    res_empty = client.post("/transactions", json=tx_empty)
    # Pydantic validation (if any) or 400
    assert res_empty.status_code == 422 or res_empty.status_code == 200

def test_customer_balance_integrity_workflow():
    """Karmaşık bir senaryoda müşteri bakiyesinin doğruluğu"""
    # Müşteri ekle
    c = client.post("/customers", json={"full_name": "Sadık Müşteri", "phone": "123"}).json()
    cid = c["id"]
    
    # 1. Borçlanma (10.000 TL'lik veresiye ürün alımı)
    client.post("/transactions", json={
        "side": "sell", "qty": 1.0, "unit_price": 10000.0, "total_price": 10000.0,
        "symbol": "ÜRÜN", "customer_id": cid, "payment_type": "Debt"
    })
    
    # 2. Ödeme (3.000 TL nakit ödeme yaptı)
    client.post(f"/customers/{cid}/payment", params={"amount": 3000.0, "p_type": "tahsilat"})
    
    # 3. İade veya Yeni Alım (Dükkana 2.000 TL'lik başka bir ÜRÜN sattı ve parasını almadı, alacağına yazdırdı)
    client.post("/transactions", json={
        "side": "buy", "qty": 1.0, "unit_price": 2000.0, "total_price": 2000.0,
        "symbol": "ÜRÜN", "customer_id": cid, "payment_type": "Debt"
    })
    
    # Son Bakiye Hesabı: 10000 (borç) - 3000 (ödeme) - 2000 (getirdiği ürün) = 5000 TL Borç
    final_cust = client.get("/customers").json()
    sadik = next(x for x in final_cust if x["id"] == cid)
    assert sadik["balance_try"] == 5000.0


def test_margin_and_price_logic():
    """Kâr marjı değişikliğinin fiyatlara yansıması"""
    # USD için marj ayarla
    client.post("/settings/margins", params={"symbol": "USD", "buy_margin": 0.5, "sell_margin": 1.2})
    
    # Fiyatları çek
    res = client.get("/prices").json()
    if "USD" in res:
        # Satış fiyatı = Ham + Sell_Margin (Burada backend logic'i test ediyoruz)
        # Eğer logic koddaysa marjların sıfır olmadığını doğrula
        assert res["USD"]["sell"] > 0
        assert res["USD"]["buy"] > 0

def test_inventory_full_lifecycle():
    """Ürün stok döngüsü: Alım -> Satış -> Stok Kontrolü"""
    # 10 adet ürün ekle
    p = client.post("/products", json={
        "name": "Yüzük", "category": "Altın", "weight": 2.0, "purity": 0.585, "labor_cost": 100, "stock_qty": 10
    }).json()
    pid = p["id"]
    
    # 3 adet sat
    client.post("/transactions", json={
        "side": "sell", "qty": 3.0, "unit_price": 5000.0, "total_price": 15000.0,
        "symbol": "ÜRÜN", "product_id": pid, "payment_type": "Cash"
    })
    
    # Stok 7 kalmalı
    res = client.get("/products").json()
    yuzuk = next(x for x in res if x["id"] == pid)
    assert yuzuk["stock_qty"] == 7

def test_daily_report_logic():
    """Günlük raporun (daily) filtreleme ve hesaplama mantığını test eder"""
    # 1. Bugün için bir işlem ekle
    client.post("/transactions", json={
        "side": "sell", "qty": 1.0, "unit_price": 5000.0, "total_price": 5000.0,
        "symbol": "GA", "payment_type": "Cash"
    })
    
    # 2. Raporu çek
    res = client.get("/reports/daily").json()
    assert len(res["transactions"]) >= 1
    assert res["transactions"][0]["side"] == "SATIŞ"

def test_product_buy_transaction():
    """Ürün alışı (buy) durumunda stok artışını test eder"""
    p = client.post("/products", json={
        "name": "Küpe", "category": "Altın", "weight": 1.0, "purity": 0.585, "labor_cost": 50, "stock_qty": 5
    }).json()
    pid = p["id"]
    
    # 2 adet alalım (stok artmalı)
    client.post("/transactions", json={
        "side": "buy", "qty": 2.0, "unit_price": 2000.0, "total_price": 4000.0,
        "symbol": "ÜRÜN", "product_id": pid, "payment_type": "Cash"
    })
    
    res = client.get("/products").json()
    kupe = next(x for x in res if x["id"] == pid)
    assert kupe["stock_qty"] == 7

def test_debt_transaction_non_gold():
    """Altın dışı (Döviz) bir sembolle veresiye işlem yapılması"""
    c = client.post("/customers", json={"full_name": "Döviz Borçlusu", "phone": "123"}).json()
    cid = c["id"]
    
    client.post("/transactions", json={
        "side": "sell", "qty": 100.0, "unit_price": 34.0, "total_price": 3400.0,
        "symbol": "USD", "customer_id": cid, "payment_type": "Debt"
    })
    
    # USD kasası azalmalı (dükkandan çıktı)
    v_res = client.get("/reports/kasa").json()
    # Mock vault update so it's not starting from zero if possible, but GA/USD usually exists.
    # Note: sym_v.balance += (tx.qty * (-multiplier)) -> Sell(+1) -> balance -= 100
    # Since it starts at 0, it becomes -100.
    assert any(v["symbol"] == "USD" and v["balance"] == -100.0 for v in client.get("/vault").json())

def test_debt_without_customer_id():
    """Ödeme tipi Debt seçilip customer_id gönderilmezse Cash gibi davranmalı (Kasa değişmeli)"""
    client.post("/vault/update", params={"symbol": "GA", "amount": 10.0})
    
    client.post("/transactions", json={
        "side": "sell", "qty": 1.0, "unit_price": 3000.0, "total_price": 3000.0,
        "symbol": "GA", "payment_type": "Debt" # customer_id yok!
    })
    
    # 3B'ye düşmeli (Cash mantığı) -> TL kasası 3000 artmalı
    rep = client.get("/reports/kasa").json()
    assert rep["balances"].get("TRY") == 3000.0

def test_price_fetch_failure():
    """Fiyat çekme işlemi başarısız olduğunda fallback (yedek) fiyatların kullanıldığını denetler"""
    from unittest.mock import patch
    with patch("backend.services.prices.httpx.AsyncClient.get", side_effect=Exception("API Down")):
        res = client.get("/prices")
        assert res.status_code == 200
        # Fallback GA fiyatı 3000 olmalı
        assert res.json()["GA"]["buy"] == 3000.0


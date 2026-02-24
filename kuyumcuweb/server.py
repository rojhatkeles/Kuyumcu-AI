from fastapi import FastAPI, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
import os
import datetime

app = FastAPI(title="Kuyumcu Pro Web Backend")

# Statik dosyaları (HTML, CSS, JS, Image) sunmak için mount ediyoruz
# Bu sayede root '/' dizinine gelindiğinde index.html görünecek
script_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=script_dir), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(script_dir, "index.html"))

@app.get("/hero.png")
async def get_hero():
    return FileResponse(os.path.join(script_dir, "hero.png"))

@app.get("/style.css")
async def get_style():
    return FileResponse(os.path.join(script_dir, "style.css"))

@app.get("/script.js")
async def get_script():
    return FileResponse(os.path.join(script_dir, "script.js"))

# 📥 İndirme İsteği Takibi
@app.get("/api/download")
async def download_app():
    # Burada indirme sayısını bir dosyaya veya DB'ye kaydedebiliriz
    with open(os.path.join(script_dir, "stats.log"), "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()}: Bir kullanıcı indirme başlattı.\n")
    
    # Şimdilik örnek bir dosya ismi dönüyoruz (Dosya gerçekten varsa FileResponse ile gönderilir)
    return {"status": "success", "message": "İndirme başlatılıyor...", "file": "KuyumcuPro_Setup_v6.exe"}

# ✉️ İletişim Formu İşleme
@app.post("/api/contact")
async def handle_contact(name: str = Form(...), email: str = Form(...), message: str = Form(...)):
    # Gelen mesajı log dosyasına kaydediyoruz (İleride mail atma kodu buraya gelecek)
    log_entry = f"{datetime.datetime.now()} | Kimden: {name} ({email}) | Mesaj: {message}\n"
    with open(os.path.join(script_dir, "messages.txt"), "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    return JSONResponse(content={"status": "ok", "message": "Mesajınız başarıyla iletildi. Sizinle en kısa sürede iletişime geçeceğiz."})

@app.get("/boss")
async def read_boss():
    return FileResponse(os.path.join(script_dir, "boss.html"))

@app.get("/boss.css")
async def get_boss_css():
    return FileResponse(os.path.join(script_dir, "boss.css"))

# 🔑 LİSANS VE BULUT SENKRONİZASYON (KULUÇKA MODU)
VALID_LICENSES = ["PRO-MASTER-2026", "DEMO-7DAYS-XYZ"] # Örnek aktif lisanslar
DÜKKAN_REPORTS = {} # {license_key: financial_snapshot}

@app.get("/api/license/verify")
async def verify_license(key: str):
    if key in VALID_LICENSES:
        return {"status": "valid", "tier": "PREMIUM"}
    return JSONResponse(status_code=400, content={"status": "invalid", "message": "Geçersiz lisans anahtarı."})

@app.get("/api/sync/get_latest")
async def get_latest_report(key: str):
    """Boss panelinin dükkan verisini çektiği uç nokta"""
    if key in DÜKKAN_REPORTS:
        return DÜKKAN_REPORTS[key]
    raise HTTPException(status_code=404, detail="Rapor bulunamadı.")

@app.post("/api/sync/report")
async def sync_report(key: str, data: dict):
    """Masaüstü uygulamadan gelen finansal özeti kaydeder (Bulut Panel Hazırlığı)"""
    if key not in VALID_LICENSES:
        raise HTTPException(status_code=403, detail="Yetkisiz erişim.")
    
    DÜKKAN_REPORTS[key] = {
        "last_sync": datetime.datetime.now().isoformat(),
        "data": data
    }
    # Burada veriyi ileride patrona webden göstermek için saklıyoruz
    with open(os.path.join(script_dir, "cloud_reports.log"), "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()}: {key} dükkanı senkronize edildi.\n")
    
    return {"status": "success", "message": "Bulut senkronizasyonu tamamlandı."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

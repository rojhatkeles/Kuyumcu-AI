import subprocess
import sys
import time
import os

print("💎 Kuyumcu Pro AI Başlatılıyor...")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_SCRIPT = os.path.join(BASE_DIR, "backend", "run_server.py")
WEB_SERVER_SCRIPT = os.path.join(BASE_DIR, "kuyumcuweb", "server.py")
FRONTEND_SCRIPT = os.path.join(BASE_DIR, "frontend", "run_client.py")

# 1. Arka planda masaüstü sunucuyu (API) başlat
server_process = subprocess.Popen(
    [sys.executable, BACKEND_SCRIPT],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    cwd=BASE_DIR
)

# 2. Arka planda WEB (SaaS/Patron) sunucusunu başlat
web_process = subprocess.Popen(
    [sys.executable, WEB_SERVER_SCRIPT],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    cwd=BASE_DIR
)

print("⏳ Sistem hazırlanıyor, lütfen bekleyin...")
time.sleep(3) # Sunucuların hazır olması için 3 saniye bekle

# 3. Arayüzü (GUI) başlat
print("🖥️  Arayüz açılıyor...")
client_process = subprocess.Popen(
    [sys.executable, FRONTEND_SCRIPT],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    cwd=BASE_DIR
)

# 3. Kasiyer arayüzü kapatana kadar bekle
client_process.wait()

# 4. Arayüz kapatıldığında, tüm arka plan sunucularını kapat
print("🛑 Program kapatıldı. Sisteme güvenli çıkış yapılıyor...")
server_process.terminate()
web_process.terminate()
server_process.wait()
web_process.wait()
print("Hoşçakalın! 👋")

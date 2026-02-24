import uvicorn
import sys
import os

# Proje ana dizinini yola ekle, böylece backend.* importları çalışır
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    # Konsol kirliliğini önlemek için log_level='error' ve access_log=False yapıyoruz
    # Ayrıca hızı artırmak ve logları kısmak için reload=False yapıyoruz.
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False, access_log=False, log_level="error")

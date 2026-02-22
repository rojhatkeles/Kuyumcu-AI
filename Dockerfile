# Base image
FROM python:3.12-slim

# Çalışma dizini oluştur ve ayarla
WORKDIR /app

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Uvicorn ile uygulamayı çalıştır
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

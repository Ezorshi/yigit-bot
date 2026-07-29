# Python 3.11 kullan (3.14'te sorun olabiliyor)
FROM python:3.11-slim

# libsodium kur (ses için gerekli)
RUN apt-get update && apt-get install -y \
    libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Gereksinimleri kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm dosyaları kopyala
COPY . .

# Port (Render için)
EXPOSE 10000

# Bot'u başlat
CMD ["python", "discord_bot.py"]

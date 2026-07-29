FROM python:3.11-slim

# libsodium'u zorla kur (geliştirme paketleriyle)
RUN apt-get update && apt-get install -y \
    libsodium-dev \
    libsodium23 \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# PyNaCl'yi yeniden derle
ENV SODIUM_INSTALL=system

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 10000
CMD ["python", "discord_bot.py"]

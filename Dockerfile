FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка wine для MT5 (Linux)
RUN apt-get update && apt-get install -y wine64 wine32 && rm -rf /var/lib/apt/lists/*

# Копирование кода
COPY . .

# Создание папок
RUN mkdir -p /app/ai_state /backups

CMD ["python", "run.py"]

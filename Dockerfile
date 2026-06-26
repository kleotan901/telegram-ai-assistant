FROM python:3.12-slim

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Робоча директорія всередині контейнера
WORKDIR /app

# Копіюємо залежності окремо — щоб Docker кешував цей шар
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь проект
COPY . .

# Відкриваємо порт
EXPOSE 8000

# Запуск — буде перевизначений у docker-compose
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

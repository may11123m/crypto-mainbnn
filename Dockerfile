FROM python:3.11-slim

# تنظیم متغیرهای محیطی پایتون
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# نصب ابزارهای مورد نیاز سیستم‌عامل
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# کپی و نصب نیازمندی‌های پایتون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کامل پروژه به داخل کانتینر
COPY . .

# اجرای ربات
CMD ["python", "main.py"]
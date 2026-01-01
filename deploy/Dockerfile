FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY backend/ ./backend/
COPY data/ ./data/

# 실행
ENV PYTHONPATH=/app/backend
WORKDIR /app/backend
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

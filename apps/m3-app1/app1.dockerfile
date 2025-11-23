FROM python:3.11-slim

WORKDIR /app

# requirements 먼저 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 전체 복사
COPY . /app

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    HOST=0.0.0.0 \
    PORT=8080 \
    PYTHONPATH=/app

# 데이터 저장 경로 준비
RUN mkdir -p /app/data

EXPOSE 8080

# FastAPI 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]


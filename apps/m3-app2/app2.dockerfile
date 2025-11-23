FROM python:3.11-slim

WORKDIR /app

# requirements 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 전체 복사
COPY . /app

# 환경 변수
ENV PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    HOST=0.0.0.0 \
    PORT=8085 \
    PYTHONPATH=/app

EXPOSE 8085

# FastAPI 실행
CMD ["uvicorn", "main2:app", "--host", "0.0.0.0", "--port", "8085"]


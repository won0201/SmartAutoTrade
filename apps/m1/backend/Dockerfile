FROM python:3.11-slim

WORKDIR /app

# 필요한 시스템 패키지 설치 (필요하다면 주석 해제 가능)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements 설치
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# app 코드 복사
COPY app/ /app/app/

# FastAPI 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7101"]


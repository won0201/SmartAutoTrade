FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app 폴더만 복사해서 /app/app 에 넣는다
COPY app ./app

# uvicorn이 app/main.py 안의 app 객체를 사용
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

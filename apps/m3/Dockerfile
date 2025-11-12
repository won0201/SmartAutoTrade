FROM python:3.11-slim
WORKDIR /app
COPY app/ /app/
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
ENV PORT=7101
CMD ["python", "main.py"]

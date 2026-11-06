FROM ghcr.io/esphome/esphome:latest

RUN pip install --no-cache-dir fastapi uvicorn python-multipart

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 6052

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "6052"]

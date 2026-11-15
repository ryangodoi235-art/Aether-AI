FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-forecast.txt requirements-features.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-forecast.txt -r requirements-features.txt
COPY backend ./backend
COPY frontend ./frontend
COPY config ./config
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.cloud:app", "--host", "0.0.0.0", "--port", "8000"]

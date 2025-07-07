FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app/src:/app
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "9003"] 
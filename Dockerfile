FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get upgrade -y zlib1g && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 10001 app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gateway ./gateway
RUN chown -R app:app /app

USER 10001
EXPOSE 8000
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Deutsche Stimme zum Vorlesen (lokal, ~60 MB)
ARG STIMME=de_DE-thorsten-medium
RUN python -m piper.download_voices --data-dir /app/stimmen ${STIMME}

COPY momo ./momo

# Ohne Root-Rechte laufen; Datenordner gehört dem Dienstnutzer
RUN useradd --system --uid 10001 --home /daten momo \
    && mkdir -p /daten && chown -R momo /daten
USER momo

CMD ["python", "-m", "momo"]

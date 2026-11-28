FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 RCLONE_CONFIG=/daten/rclone.conf
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg rclone ca-certificates tesseract-ocr tesseract-ocr-deu poppler-utils fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Deutsche Stimme zum Vorlesen (lokal, ~60 MB)
ARG STIMME=de_DE-thorsten-medium
RUN python -m piper.download_voices --data-dir /app/stimmen ${STIMME}

# Zuhören: Whisper-Modell lokal (small ≈ 500 MB, Wahl über Build-Argument und MOMO_WHISPER)
ARG WHISPER=small
RUN python -c "from faster_whisper import download_model; download_model('${WHISPER}', output_dir='/app/whisper/${WHISPER}')"

# Optional: Claude Code für den Anschluss claude-abo (zum Testen mit einem Claude-Abo)
ARG MIT_CLAUDE=0
RUN if [ "$MIT_CLAUDE" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends nodejs npm \
      && npm install -g --omit=dev @anthropic-ai/claude-code \
      && npm cache clean --force && rm -rf /var/lib/apt/lists/*; \
    fi

COPY momo ./momo
COPY tools ./tools

# Ohne Root-Rechte laufen; Datenordner gehört dem Dienstnutzer
RUN useradd --system --uid 10001 --home /daten momo \
    && mkdir -p /daten && chown -R momo /daten
USER momo

CMD ["python", "-m", "momo"]

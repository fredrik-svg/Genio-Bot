FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev ffmpeg sox alsa-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install -U pip wheel && pip install -r requirements.txt
COPY . .
CMD ["python", "src/main.py", "--config", "config.yaml"]

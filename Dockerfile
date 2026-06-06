FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium and all its system dependencies via Playwright
RUN playwright install chromium --with-deps

COPY app.py bluebot.py task.py ./

# Xvfb virtual display — browser runs non-headless, indistinguishable from a real desktop
ENV DISPLAY=:99
ENV HEADLESS=false

EXPOSE 8000

CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & uvicorn app:app --host 0.0.0.0 --port 8000"]

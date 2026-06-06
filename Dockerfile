FROM python:3.12-slim

WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium and all its system dependencies via Playwright
RUN playwright install chromium --with-deps

COPY app.py bluebot.py task.py ./

# Use headless=new mode (Chrome 112+) — far harder to fingerprint than old headless,
# and avoids GPU/display issues that cause CDP timeouts on Xvfb in containers.
ENV HEADLESS=true
ENV IN_DOCKER=true

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

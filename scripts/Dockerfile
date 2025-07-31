FROM python:3.9-slim-bullseye

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    jq \
    dos2unix \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir Flask Flask-Cors

COPY scripts/ .

RUN dos2unix /app/run_full_test.sh && \
    chmod +x /app/run_full_test.sh && \
    chmod +x /app/generate_html_report.py

EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
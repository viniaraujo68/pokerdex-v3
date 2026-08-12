FROM python:3.12-slim

WORKDIR /app

# System deps for argon2-cffi build are already in the wheel; keep image slim.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts

# SQLite lives on the mounted volume.
ENV POKERDEX_DATABASE_URL=sqlite:////data/pokerdex.db
ENV POKERDEX_COOKIE_SECURE=true
ENV POKERDEX_CORS_ORIGINS=

EXPOSE 8000
# --proxy-headers + --forwarded-allow-ips: the edge proxy is the only client uvicorn ever
# sees, so without trusting its X-Forwarded-For every request would share one rate-limit
# bucket (and logs would show the proxy's IP). Safe here because the container port is not
# reachable from outside the compose network.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips=*"]

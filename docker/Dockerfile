FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
# backend/requirements.txt does `-r requirements-core.txt` (and the split-out ONNX Runtime files),
# so ALL of them must be present before pip install -- copying only requirements.txt made the
# install fail with "Could not open requirements file: backend/requirements-core.txt".
COPY backend/requirements*.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
# nova_agent/ (the N.O.V.A. clinical reasoning engine -- see backend/app/services/nova_service.py)
# lives at the repo root, a sibling of backend/, not inside it. No new pip dependency: nova_agent's
# own requirement (pydantic>=2.6,<3) is already satisfied by backend/requirements-core.txt's pinned
# pydantic==2.13.5. Landing it at /app/nova_agent -- a sibling of /app/backend, matching the repo's
# own layout -- means nova_service.py's sys.path bootstrap (which inserts its own parents[3], i.e.
# the directory ABOVE backend/) finds it without any extra ENV PYTHONPATH: WORKDIR /app is already
# on sys.path when `python -m uvicorn ...` runs from here (see nova_service.py's own comment on
# this same bootstrap for local dev / pytest).
COPY nova_agent/ /app/nova_agent/
COPY --from=frontend /build/dist /app/frontend/dist
RUN useradd --create-home --uid 10001 synex && mkdir -p /app/runtime && chown -R synex:synex /app/runtime
USER synex
ENV SYNEX_AUDIT_PATH=/app/runtime/audit.sqlite3
ENV SYNEX_PROVIDER=cpu
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]

# Production runtime image for the N.O.V.A. Doctor Agent decision-support API.
#
# Deliberately separate from docker/Dockerfile (that one builds the unrelated, pre-existing
# SynexAgent project vendored elsewhere in this repo) and from the competition submission
# artifact (scripts/build_nova_submission.py never touches this file or production/ at all --
# see production/__init__.py). Build from the REPO ROOT so it can copy nova_agent/ alongside
# production/:
#   docker build -f production/Dockerfile -t nova-doctor-agent:local .
#
# Small base image, non-root user, no baked-in secrets (NOVA_API_KEYS/NOVA_DATABASE_URL/etc are
# supplied at runtime via environment variables or a secret manager, never COPYed into the image),
# and a HEALTHCHECK against the real /health endpoint.

FROM python:3.12-slim AS base

WORKDIR /app

COPY requirements-nova.txt /app/requirements-nova.txt
COPY production/requirements.txt /app/production/requirements.txt
# production/requirements.txt's "-r ../requirements-nova.txt" is relative to ITS OWN path, so it
# must land at /app/production/requirements.txt (a sibling of /app/nova_agent, not flattened into
# /app directly) for that reference to resolve to /app/requirements-nova.txt correctly.
RUN pip install --no-cache-dir -r /app/production/requirements.txt

COPY nova_agent/ /app/nova_agent/
COPY production/ /app/production/

RUN useradd --create-home --uid 10001 nova \
    && mkdir -p /app/runtime \
    && chown -R nova:nova /app

USER nova

ENV NOVA_ENV=production \
    NOVA_LLM_PROVIDER=mock \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["python", "-m", "uvicorn", "production.api:app", "--host", "0.0.0.0", "--port", "8000"]

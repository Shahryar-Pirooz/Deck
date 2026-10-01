FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && python -m pip uninstall -y pip >/dev/null 2>&1 || true

ENV TERM=xterm-256color

# Run the module directly so the image does not depend on console-script
# filename casing or PATH details.
ENTRYPOINT ["python", "-m", "deck.cli"]

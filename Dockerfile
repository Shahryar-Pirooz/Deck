# Docker TUI Manager — container image.
#
# Build:  docker build -t deck:<version> .
# Run:    the manager needs the host Engine shared in plus an interactive
#         terminal (see README "Running as a container"). Sharing Engine
#         access grants full control of the host — see the privilege warning
#         in the run documentation before using this image.

FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install .

ENTRYPOINT ["Deck"]

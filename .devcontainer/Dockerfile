FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Das Basisimage kann eine externe Yarn-Paketquelle enthalten, deren Signaturschlüssel
# unabhängig vom Projekt abläuft. Yarn wird für diesen Testbench nicht benötigt.
# Entfernen verhindert, dass ein fremder Repository-Key den reproduzierbaren
# Codespaces-/Dev-Container-Build blockiert.
RUN rm -f /etc/apt/sources.list.d/yarn*.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       curl jq shellcheck unzip \
    && rm -rf /var/lib/apt/lists/*

FROM python:3.12-slim


COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

   # Copy the project into the intermediate image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# Ajouter le script d'entrée
COPY docker/database/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Utiliser le script comme point d'entrée
ENTRYPOINT ["/entrypoint.sh"]
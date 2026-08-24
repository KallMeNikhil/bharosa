# The backend image, used for both the API and the migration runner.
#
# One image serves both because a migration must run exactly the code the API
# is about to run. Building them separately would let the two drift, which is
# the failure that produces a schema the application cannot use.

FROM python:3.12-slim

# psycopg is installed as a binary wheel and carries its own libpq, so no build
# toolchain is needed here. curl is present only for the container healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY . .

# The dev extra brings pytest and ruff, so the same container can run the suite
# without a second image to keep in step.
RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

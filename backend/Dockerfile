FROM python:3.11-slim

# Create a system user 'appuser' with UID 1000
RUN useradd -m -u 1000 appuser

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app
COPY ./scripts /code/scripts

# Pre-create writable directories for database and self-healing ML models
RUN mkdir -p /code/db /code/app/ml/artifacts && \
    chown -R appuser:appuser /code/db /code/app/ml/artifacts

# Expose Hugging Face Space default port
EXPOSE 7860

# Switch to the non-root application user
USER appuser

# Configure database to be stored in the writable /code/db directory
ENV DATABASE_URL="sqlite+aiosqlite:///./db/railmind_local.db"

# Seed database and run uvicorn server
CMD python scripts/seed_railway_graph.py && uvicorn app.main:app --host 0.0.0.0 --port 7860


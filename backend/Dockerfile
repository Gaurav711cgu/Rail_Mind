FROM python:3.11-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app
COPY ./scripts /code/scripts

# Expose Hugging Face Space default port
EXPOSE 7860

# Make /code owned by the app user (UID 1000) for security and writability
RUN chown -R 1000:1000 /code

# Seed database and run uvicorn server
CMD python scripts/seed_railway_graph.py && uvicorn app.main:app --host 0.0.0.0 --port 7860

# A container image is just a recipe for "everything needed to run the app."
# Cloud Run runs this container; building it teaches what "deploy" really means.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (in their own layer) so Docker can cache them and
# only reinstall when requirements.txt changes — faster rebuilds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY app ./app

# Cloud Run tells the container which port to listen on via the PORT env var
# (defaults to 8080). We bind uvicorn to 0.0.0.0 so it's reachable from outside
# the container. Shell form lets ${PORT} expand at runtime.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

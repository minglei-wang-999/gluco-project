# Use Python 3.11 slim as base image
FROM python:3.11-slim


# Set working directory
WORKDIR /app

# Copy the rest of the application
COPY app/ ./app
COPY alembic/ ./alembic
COPY alembic.ini ./alembic.ini
COPY requirements.txt ./requirements.txt

RUN pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple \
    && pip config set global.trusted-host mirrors.cloud.tencent.com \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Command to run migrations and then start the application
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 
# Pull base image
FROM python:3.12.2-slim-bookworm

ARG DATABASE_URL
ARG DEBUG
ARG SECRET_KEY

ENV DATABASE_URL=${DATABASE_URL}
ENV DEBUG=${DEBUG}
ENV SECRET_KEY=${SECRET_KEY}

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create and set work directory called `app`
RUN mkdir -p /code
WORKDIR /code

# Install dependencies
COPY requirements.txt /tmp/requirements.txt

RUN set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

# Copy local project
COPY . /code/

# Expose port 8000
EXPOSE 80

# Use gunicorn on port 8000
CMD ["gunicorn", "--bind", ":80", "--workers", "5", "config.wsgi"]
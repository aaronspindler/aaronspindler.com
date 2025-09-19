FROM library/python:3.12.2-alpine

RUN apk update && apk upgrade && apk add --no-cache make g++ bash git openssh postgresql-dev curl

# Define build-time arguments
ARG DATABASE_URL
ARG REDIS_URL
ARG DEBUG

# Set environment variables
ENV DATABASE_URL=${DATABASE_URL}
ENV REDIS_URL=${REDIS_URL}
ENV DEBUG=${DEBUG}

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY ./requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt
COPY ./ /usr/src/app

EXPOSE 80

RUN python manage.py collectstatic --no-input
RUN python manage.py migrate --no-input

# Add healthcheck
HEALTHCHECK --interval=10s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/healthcheck || exit 1

CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:80", "--workers", "4", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]
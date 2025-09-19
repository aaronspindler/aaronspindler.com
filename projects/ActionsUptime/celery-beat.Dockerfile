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

CMD ["celery", "--app", "config.celery", "beat", "--loglevel", "info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]
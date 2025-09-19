FROM library/python:3.10-alpine

RUN apk update && apk upgrade && apk add --no-cache make g++ bash git openssh postgresql-dev curl

# Define build-time arguments
ARG DATABASE_URL
ARG REDIS_URL
ARG DEBUG
ARG CELERY_BROKER_URL

# Set environment variables
ENV DATABASE_URL=${DATABASE_URL}
ENV REDIS_URL=${REDIS_URL}
ENV DEBUG=${DEBUG}
ENV CELERY_BROKER_URL=${CELERY_BROKER_URL}

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY ./requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install flower
COPY ./ /usr/src/app

EXPOSE 5555

CMD ["celery", "flower", "--app", "config.celery", "--loglevel", "info", "--persistent", "--db=/usr/src/app/flower.db"]
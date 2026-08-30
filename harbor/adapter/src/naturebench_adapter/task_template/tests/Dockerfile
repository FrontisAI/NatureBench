FROM python:3.11.10-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . /tests/
RUN chmod +x /tests/test.sh

WORKDIR /tests

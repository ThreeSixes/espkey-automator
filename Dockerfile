# TODO: TRY THIS
# https://tech.zarmory.com/2018/09/docker-multi-stage-builds-for-python-app.html
#


FROM python:3.12.4-alpine AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1
#ENV PYTHONUNBUFFERED=1

RUN mkdir dist/

# Upgrade pip, install pipenv.
RUN python -m pip install --upgrade pip && pip install pipenv

# Set up a venv with our data.
RUN python -m venv /build/dist
ENV PATH="/build/dist:$PATH" VIRTUAL_ENV="/build/dist"

COPY Pipfile Pipfile.lock
RUN pipenv install
RUN rm Pipfile Pipfile.lock

COPY src src/


# Runner
FROM python:3.12.4-alpine

WORKDIR /app

# Point to our already-copied venv.
ENV PATH="/app/dist:$PATH" VIRTUAL_ENV="/app/dist"

COPY --from=builder /build/ /app/

ENTRYPOINT [ "python", "src/espkey_automator.py" ]
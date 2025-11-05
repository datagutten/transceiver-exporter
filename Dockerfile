FROM python:3.12-slim-bookworm as builder

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip poetry poetry-plugin-export

COPY ./pyproject.toml .
# COPY ./poetry.lock .

RUN poetry export -f requirements.txt --output requirements.txt
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r ./requirements.txt


#########
# FINAL #
#########

FROM python:3.12-slim-bookworm

COPY --from=builder /usr/src/app/wheels /wheels
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

COPY ./src .

CMD ["python", "./exporter.py"]
EXPOSE 8000
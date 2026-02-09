FROM cgr.dev/chainguard/python:latest-dev@sha256:98d6572fd0ba0414830ee95a28751d5e397b9575daf47872098acfb4050c0b22 AS builder

#force build

COPY . /app

WORKDIR /app
ENV PATH=/home/nonroot/.local/bin:$PATH

# hadolint ignore=DL4006
RUN wget -q -O - https://install.python-poetry.org | python -
RUN poetry install --no-root;

FROM cgr.dev/chainguard/python:latest@sha256:049302d2fc1d2b24c054d812eadd8c3d6321352d0cbc0d2b96b68d809946ec5b
USER nonroot
ENV DB_HOST localhost
ENV DB_NAME postgres
ENV DB_USER postgres
ENV DB_PASS postgres
ENV DB_PORT 5432

COPY --from=builder /app /app
COPY --from=builder /home/nonroot /home/nonroot

WORKDIR /app

EXPOSE 8080
ENV PATH=$PATH:/home/nonroot/.local/bin

HEALTHCHECK CMD curl --fail http://localhost:8080/health || exit 1

ENTRYPOINT ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

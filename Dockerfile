FROM cgr.dev/chainguard/python:latest-dev@sha256:9f720cffd75a6fdbfb0482c68c9d4c2bcd7883e104faf6bf81af52c7a299b2e9 AS builder

#force build

COPY . /app

WORKDIR /app
RUN python -m pip install --no-cache-dir -r requirements.txt  --require-hashes --no-warn-script-location;

FROM cgr.dev/chainguard/python:latest@sha256:be8106b35d26afee7e4c81efc80cda19e60a3b20bc759f2f71e799eea3d3eaf6
USER nonroot
ENV DB_HOST localhost
ENV DB_NAME postgres
ENV DB_USER postgres
ENV DB_PASS postgres
ENV DB_PORT 5432

COPY --from=builder /app /app
COPY --from=builder /home/nonroot/.local /home/nonroot/.local

WORKDIR /app

EXPOSE 8080
ENV PATH=$PATH:/home/nonroot/.local/bin

HEALTHCHECK CMD curl --fail http://localhost:8080/health || exit 1

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

FROM cgr.dev/chainguard/python:latest-dev@sha256:7dee8919dd14a2bf91e93d8848519819e806a4a6d3aff8b7ea8fbf5bbc2d71e9 AS builder

#force build

COPY . /app

WORKDIR /app
RUN python -m pip install --no-cache-dir -r requirements.txt  --require-hashes --no-warn-script-location;

FROM cgr.dev/chainguard/python:latest@sha256:c8c58449cd64727cfca03206b798ee9f3d64f8930273855db573538e023150a0
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

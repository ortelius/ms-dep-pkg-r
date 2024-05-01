FROM cgr.dev/chainguard/python:latest-dev@sha256:59370b0adb1cb6c95e8bbc5f10e2f2614be2cb7b5ef3072d1c18f62f5bed60ce AS builder

#force build

COPY . /app

WORKDIR /app
RUN python -m pip install --no-cache-dir -r requirements.txt  --require-hashes --no-warn-script-location;

FROM cgr.dev/chainguard/python:latest@sha256:f3c4aadce2bd015ec36a777eface9389cb5cf8a0656bd85d7a9b8ce1cfbfac1e
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

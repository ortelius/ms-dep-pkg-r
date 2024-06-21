FROM cgr.dev/chainguard/python:latest-dev@sha256:8a5b1f0314ae05f1161cd97e4191bf2e176f78a837bf2e356bcf63ed1584dd84 AS builder

#force build

COPY . /app

WORKDIR /app
RUN python -m pip install --no-cache-dir -r requirements.txt  --no-warn-script-location;

FROM cgr.dev/chainguard/python:latest@sha256:944f0e85bf1ba7b20d2755b9be05b5cb155aa8624c11cfae2126786428343202
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

FROM cgr.dev/chainguard/python:latest-dev@sha256:223b4c531fecf6a139e09c0d5ab44d439f5ea1d51620115ed784ee67cc64844a AS builder
COPY . /app

WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt --require-hashes --no-warn-script-location;

FROM cgr.dev/chainguard/python:3.11.2@sha256:223b4c531fecf6a139e09c0d5ab44d439f5ea1d51620115ed784ee67cc64844a
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

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

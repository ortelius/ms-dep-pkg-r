FROM cgr.dev/chainguard/python:latest-dev@sha256:255af1bad580e902ae0cf634cee6cdb83fbd7047513b11a7595dfc98c8422e5c AS builder

#force build

COPY . /app

WORKDIR /app
ENV PATH=/home/nonroot/.local/bin:$PATH

# hadolint ignore=DL4006
RUN wget -q -O - https://install.python-poetry.org | python -
RUN poetry install --no-root;

FROM cgr.dev/chainguard/python:latest@sha256:bb4f22b100e31fc42451710ac2ccafe198c3d2d5bb17a309033a782f5c8685ea
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

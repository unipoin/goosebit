# Production image of the unipoin fork, built from the checked-out source.
# Unlike docker/Dockerfile (installs the released package from PyPI) and
# docker/dev.dockerfile (unpinned dependencies, remote-pdb), all runtime
# dependencies come from poetry.lock and are verified by hash.
# Build context: repository root.

FROM python:3.13.7-alpine@sha256:9ba6d8cbebf0fb6546ae71f2a1c14f6ffd2fdab83af7fa5669734ef30ad48844 AS builder

# Build tooling with all transitive dependencies, every package checked against its hash
COPY .github/unipoin/requirements-build.txt /tmp/requirements-build.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements-build.txt

WORKDIR /src

# Export first so the layer is cached as long as the lock file is unchanged.
# Fails if poetry.lock does not match pyproject.toml.
COPY pyproject.toml poetry.lock ./
# Path dependencies of the plugin groups must exist, even though they are not exported
COPY plugins ./plugins
RUN mkdir -p /out && \
    poetry export --only main --extras postgresql \
        --format requirements.txt --output /out/requirements.txt

COPY . .
RUN poetry build --format wheel && cp dist/*.whl /out/


FROM python:3.13.7-alpine@sha256:9ba6d8cbebf0fb6546ae71f2a1c14f6ffd2fdab83af7fa5669734ef30ad48844

ARG GUNICORN_VERSION=27.0.1

COPY --from=builder /out /tmp/install

RUN addgroup -g 1000 goosebit && \
    adduser -u 1000 -G goosebit -s /bin/sh -D goosebit && \
    mkdir /artifacts && \
    chown goosebit:goosebit /artifacts && \
    # Locked dependencies, every package checked against its hash
    pip install --no-cache-dir --require-hashes -r /tmp/install/requirements.txt && \
    # goosebit itself, dependencies are already installed above
    pip install --no-cache-dir --no-deps /tmp/install/*.whl && \
    # gunicorn is not part of poetry.lock
    pip install --no-cache-dir "gunicorn==${GUNICORN_VERSION}" && \
    pip check && \
    rm -rf /tmp/install

COPY docker/aerich.toml /

VOLUME /artifacts

EXPOSE 60053

USER goosebit

# We currently do not fully support multiple workers. For more information, see:
# https://github.com/UpstreamDataInc/goosebit/issues/125
ENV GUNICORN_CMD_ARGS="--workers 1 --enable-stdio-inheritance"

SHELL ["/bin/sh", "-c"]
CMD aerich --config /aerich.toml upgrade && \
    gunicorn --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:60053 goosebit:app </dev/null

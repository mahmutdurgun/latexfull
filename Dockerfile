FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LATEX_ENGINE=tectonic \
    LATEX_TIMEOUT_SECONDS=60 \
    LATEX_MAIN_FILENAME=main.tex \
    TECTONIC_CACHE_DIR=/tmp/tectonic-cache

ARG TECTONIC_VERSION=0.15.0
ARG TECTONIC_TAG=tectonic%40${TECTONIC_VERSION}
ARG TECTONIC_DOWNLOAD_URL=https://github.com/tectonic-typesetting/tectonic/releases/download/${TECTONIC_TAG}/tectonic-${TECTONIC_VERSION}-x86_64-unknown-linux-musl.tar.gz

RUN apk add --no-cache curl libgcc libstdc++ tar unzip fontconfig ttf-dejavu ghostscript texlive-full \
    && mkdir -p /tmp/tectonic-download \
    && curl -fSLo /tmp/tectonic.tar.gz "${TECTONIC_DOWNLOAD_URL}" \
    && tar -xzf /tmp/tectonic.tar.gz -C /tmp/tectonic-download \
    && find /tmp/tectonic-download -type f -name tectonic -exec mv {} /usr/local/bin/tectonic \; \
    && chmod +x /usr/local/bin/tectonic \
    && rm -rf /tmp/tectonic.tar.gz /tmp/tectonic-download \
    && mkdir -p ${TECTONIC_CACHE_DIR}

WORKDIR /service

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]


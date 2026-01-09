FROM python:3.11-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc gfortran wget libatlas-base-dev git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./docker ./docker
RUN chmod +x ./docker/entrypoint.sh

ENV DATA_DIR=/data
ENV META_PATH=/data/meta.pkl
ENV FEATURES_PATH=/data/features.npz

EXPOSE 8000
CMD ["./docker/entrypoint.sh"]

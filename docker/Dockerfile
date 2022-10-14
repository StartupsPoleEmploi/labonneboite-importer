FROM apache/airflow:2.4.1-python3.10

USER root

ARG AIRFLOW_HOME=/opt/airflow

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get -y install \
    default-mysql-client \
    default-libmysqlclient-dev \
    git \
    libpq-dev \
    gcc \
    bzip2

# copy sources
COPY . /sources

RUN chown -R "airflow:root" \
    /sources
# make all the entrypoints script executable
RUN cd /sources/docker/entrypoints && find . -exec chmod +x '{}' \;

USER airflow

WORKDIR /sources

RUN pip install poetry \ 
    && PIP_USER=0 poetry install



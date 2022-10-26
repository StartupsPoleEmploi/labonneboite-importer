FROM apache/airflow:slim-2.4.2-python3.10

USER root

ARG AIRFLOW_HOME=/opt/airflow

# setup environment
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get -y install \
    git \
    libpq-dev \
    gcc \
    bzip2 \
    default-libmysqlclient-dev

COPY pyproject.toml ${AIRFLOW_HOME}/pyproject.toml
COPY poetry.lock ${AIRFLOW_HOME}/poetry.lock

# grant access to /opt/airflow to user airflow
RUN chown -R "airflow:root" \
    /opt/airflow/

USER airflow

RUN pip install poetry && \
    pip install --no-cache-dir -r <(poetry export --format requirements.txt)

# add entry points and make them runnable
COPY docker/entrypoints ${AIRFLOW_HOME}/entrypoints
RUN cd ${AIRFLOW_HOME}/entrypoints && find . -exec chmod +x '{}' \;

# copy source code
COPY ./importer ${AIRFLOW_HOME}/



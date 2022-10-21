FROM apache/airflow:slim-2.4.1-python3.10

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

COPY docker/airflow.cfg ${AIRFLOW_HOME}/airflow.cfg
COPY pyproject.toml ${AIRFLOW_HOME}/pyproject.toml
COPY poetry.lock ${AIRFLOW_HOME}/poetry.lock

# add entry points and make them runnable
COPY docker/entrypoints ${AIRFLOW_HOME}/entrypoints
RUN cd ${AIRFLOW_HOME}/entrypoints && find . -exec chmod +x '{}' \;

# grant access to /opt/airflow to user airflow
RUN chown -R "airflow:root" \
    /opt/airflow/

USER airflow

RUN pip install --upgrade pip && \
    pip install poetry==1.1.15 && \
    pip install --user --requirement <(poetry export --format requirements.txt)

# copy source code
COPY ./importer ${AIRFLOW_HOME}/



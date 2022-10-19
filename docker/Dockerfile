FROM apache/airflow:slim-2.3.4-python3.10

USER root

ARG AIRFLOW_HOME=/opt/airflow

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

RUN chown -R "airflow:root" \
    /opt/airflow/

USER airflow

RUN pip install --upgrade pip && \
    pip install poetry && \
    pip install --user --requirement <(poetry export --format requirements.txt)

# copy source code
COPY ./importer/dags ${AIRFLOW_HOME}/dags
COPY ./importer/plugins ${AIRFLOW_HOME}/plugins


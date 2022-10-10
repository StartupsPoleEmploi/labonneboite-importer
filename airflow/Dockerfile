FROM apache/airflow:2.2.4-python3.9

USER root

ARG AIRFLOW_HOME=/opt/airflow

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get -y install \
    git \
    libpq-dev \
    gcc \
    bzip2

#ADD dags-airflow /opt/airflow/dags

COPY airflow/airflow.cfg ${AIRFLOW_HOME}/airflow.cfg

RUN chown -R "airflow:root" \
    /opt/airflow/

# USER ${AIRFLOW_UID}
USER airflow

RUN ${AIRFLOW_USER_HOME_DIR}/.local/bin/pip install --upgrade pip && \
    ${AIRFLOW_USER_HOME_DIR}/.local/bin/pip install pip-tools

COPY requirements.txt /requirements.txt

RUN ${AIRFLOW_USER_HOME_DIR}/.local/bin/pip-sync /requirements.txt


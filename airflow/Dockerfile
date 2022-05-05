FROM apache/airflow:2.2.4-python3.9

USER root 

ARG AIRFLOW_HOME=/opt/airflow 

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get -y install git

#ADD dags-airflow /opt/airflow/dags

ADD airflow.cfg /opt/airflow/airflow.cfg

RUN pip install --upgrade pip

RUN chown -R "airflow:root" /opt/airflow/

# USER ${AIRFLOW_UID}
USER airflow

ADD requirements.txt /requirements.txt

RUN pip install -r /requirements.txt

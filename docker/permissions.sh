#!/bin/bash
set -e

# MUST BE RUN BEFORE SWITCHING TO airflow USER
if [[ "$CUSTOM_UID" != "" ]]; then
    if [ $CUSTOM_UID -gt 0 ]; then
        usermod -u ${CUSTOM_UID} airflow
    fi
fi
chown -R "airflow:root" ${AIRFLOW_HOME}

mkdir -p ${AIRFLOW_HOME}/testResults
chown -R "airflow:root" ${AIRFLOW_HOME}/testResults
chmod 777 ${AIRFLOW_HOME}/testResults

mkdir -p ${AIRFLOW_HOME}/logs
chown -R "airflow:root" ${AIRFLOW_HOME}/logs

mkdir -p /var/work
chown -R "airflow:root" /var/work

mkdir -p /var/output
chown -R "airflow:root" /var/output
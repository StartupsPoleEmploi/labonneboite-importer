init: init-airflow

VIRTUAL_ENV ?= ${PWD}/venv
PYTHON = ${VIRTUAL_ENV}/bin/python
PYTHON_VERSION_FILE = .python-version
PYTHON_INSTALLED_VERSION_FILE=.installed-python-version
PYTHON_VERSION := $(shell cat ${PYTHON_VERSION_FILE})
_PIP_ADDITIONAL_REQUIREMENTS := $(shell cat requirements.txt)

.DEFAULT_GOAL := help

all: init startserver  ## init and start the local server

# Init
# ----

init: init-venv init-airflow  ## init local environement

init-airflow: init-airflow-dir init-airflow-dotenv init-airflow-basic-auth  ## init airflow (available env var : USER and PASSWORD)
	_AIRFLOW_WWW_USER_USERNAME="$${USER}" _AIRFLOW_WWW_USER_PASSWORD="$${PASSWORD}" docker-compose up airflow-init

init-airflow-dotenv:
	echo "AIRFLOW_UID=$(shell id -u)" >> .env

init-airflow-dir:
	mkdir -p ./dags ./logs ./importer

init-airflow-basic-auth:
	htpasswd -cb nginx/etc/nginx/auth/.htpasswd "${USER}" "${PASSWORD}"

init-airflow-settings:
	docker-compose run --no-deps -v ${PWD}/importer/settings:/opt/airflow/settings --rm airflow-webserver bash -c "set -xe; \
		airflow variables import /opt/airflow/settings/default.json; \
		airflow variables import /opt/airflow/settings/docker.json; \
		airflow connections list --conn-id fs_default | grep fs_default \
			|| airflow connections add fs_default --conn-type fs"

init-venv: ${PYTHON} init-pip requirements.dev.txt ${VIRTUAL_ENV}/bin/pip-sync  ## init local virtual env
	${VIRTUAL_ENV}/bin/pip-sync requirements.dev.txt

init-pip: ${PYTHON}
	${PYTHON} -m pip install --upgrade pip

# Utils
# -----

startserver:  ## Start local servers
	docker-compose up --detach


# Python virtual env
# ------------------
PYENV_ARG = --skip-existing
PYENV_CFLAGS=$(shell pkg-config --cflags libffi)
PYENV_LDFLAGS=$(shell pkg-config --libs libffi)

${PYTHON_VERSION_FILE}:
${PYTHON_INSTALLED_VERSION_FILE}: ${PYTHON_VERSION_FILE}
	pyenv --version && pyenv install --version

	CFLAGS="${PYENV_CFLAGS}" \
		LDFLAGS="${PYENV_LDFLAGS}" \
		CC="gcc-10" \
		MAKEFLAGS= \
		pyenv install ${PYENV_ARG} ${PYTHON_VERSION}
	echo ${PYTHON_VERSION} > ${PYTHON_INSTALLED_VERSION_FILE}

${PYTHON}: ${PYTHON_INSTALLED_VERSION_FILE}
	python3 -m pip install virtualenv
	python3 -m virtualenv -p ${PYTHON_VERSION} ${VIRTUAL_ENV}
	touch ${PYTHON}  # if the venv was already existing

${VIRTUAL_ENV}/bin/pip-sync: ${VIRTUAL_ENV}/bin/pip-compile
${VIRTUAL_ENV}/bin/pip-compile: ${PYTHON}
	${PYTHON} -m pip install pip-tools


# Requirements
# ------------

compile-requirements: requirements.txt  ## Compile requirements
compile-dev-requirements: requirements.dev.txt  ## Compile dev requirements

requirements.dev.txt: requirements.txt


.SUFFIXES: .in .txt
.in.txt:
	${MAKE} ${VIRTUAL_ENV}/bin/pip-compile
	${VIRTUAL_ENV}/bin/pip-compile -o $@ -v $<



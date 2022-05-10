AIRFLOW_TEST_ENV= \
	AIRFLOW_HOME=${PWD}/airflow \
	AIRFLOW__CORE__DAGS_FOLDER=${PWD}/importer/dags \
	AIRFLOW__CORE__PLUGINS_FOLDER=${PWD}/importer/plugins
TEST_FILES ?= importer
TEST_COV_ARGS ?= --cov importer --cov-fail-under  90
TEST_ARGS ?= ${TEST_COV_ARGS}

VIRTUAL_ENV ?= ${PWD}/venv
PYTHON = ${VIRTUAL_ENV}/bin/python
PYTHON_VERSION_FILE = .python-version
PYTHON_INSTALLED_VERSION_FILE=.installed-python-version
PYTHON_VERSION := $(shell cat ${PYTHON_VERSION_FILE})
_PIP_ADDITIONAL_REQUIREMENTS := $(shell cat requirements.txt)

OUTPUT_DIR	?= ./importer/var/output
AIRFLOW_UID	?= 50000

.DEFAULT_GOAL := help

all: init build startserver  ## init and start the local server

# Init
# ----

init: init-venv init-airflow  ## init local environement

init-airflow: init-airflow-dir init-airflow-basic-auth init-airflow-output-dir  ## init airflow (available env var : USER and PASSWORD)
	_AIRFLOW_WWW_USER_USERNAME="$${USER}" _AIRFLOW_WWW_USER_PASSWORD="$${PASSWORD}" docker-compose up airflow-init

init-airflow-dir:
	mkdir -p ./dags ./logs ./importer

init-airflow-basic-auth:
	htpasswd -cb nginx/etc/nginx/auth/.htpasswd "${USER}" "${PASSWORD}"

init-venv: ${PYTHON} init-pip requirements.dev.txt ${VIRTUAL_ENV}/bin/pip-sync  ## init local virtual env
	${VIRTUAL_ENV}/bin/pip-sync requirements.dev.txt

init-pip: ${PYTHON}
	${PYTHON} -m pip install --upgrade pip

init-airflow-output-dir:
	#	mkdir -p "${OUTPUT_DIR}"
	#	chown "${AIRFLOW_UID}:0" ${OUTPUT_DIR}


# Utils
# -----

build:  ## Re-build the images (required after requirements modifications)
	docker-compose build

startserver:  ## Start local servers
	docker-compose up --build --detach
	docker-compose restart


# Testing
# -------

test: test-init test-run  ## Init and run tests

test-run:  ## Run tests
	${AIRFLOW_TEST_ENV} pytest --import-mode importlib ${TEST_ARGS} ${TEST_FILES}

test-init: init-venv test-init-db test-init-variables  ## Init tests

test-init-db:
	${AIRFLOW_TEST_ENV} airflow db reset --yes

test-init-variables:
	${AIRFLOW_TEST_ENV} airflow variables import ./importer/settings/default.json
	${AIRFLOW_TEST_ENV} airflow variables import ./importer/settings/local.json

# Lint
# ----

lint: lint-flake8 lint-mypy  ## Lint and type check the project

lint-flake8:
	flake8 importer

lint-mypy:
	cd importer/plugins; mypy --config-file=../../setup.cfg . ../dags ../tests

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


# Help
# ----

help:  ## show this help
	@echo ""
	@echo "    :: ${RED}Self-documenting Makefile${RESET} ::"
	@echo "${GRAY}"
	@echo "Document targets by adding '## comment' after the target"
	@echo ""
	@echo "Example:"
	@echo "  | job1:  ## help for job 1"
	@echo "  | 	@echo \"run stuff for target1\""
	@echo "${RESET}"
	@echo "-----------------------------------------------------------------"
	@grep -E '^[a-zA-Z_0-9%-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "${TARGET_COLOR}%-30s${RESET} %s\n", $$1, $$2}'


ifneq (,$(findstring xterm,${TERM}))
RED    := $(shell tput setaf 1)
BLUE   := $(shell tput setaf 6)
GRAY   := $(shell tput dim)
RESET  := $(shell tput sgr0)
else
RED    := ""
BLUE   := ""
GRAY   := ""
RESET  := ""
endif
TARGET_COLOR=${BLUE}

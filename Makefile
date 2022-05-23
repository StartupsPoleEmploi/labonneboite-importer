AIRFLOW = ${AIRFLOW_TEST_ENV} ${VIRTUAL_ENV}/bin/airflow
AIRFLOW_TEST_ENV= \
	AIRFLOW_HOME=/tmp/airflow \
	AIRFLOW__CORE__DAGS_FOLDER=${PWD}/importer/dags \
	AIRFLOW__CORE__PLUGINS_FOLDER=${PWD}/importer/plugins
AIRFLOW_UID	?= 50000

MIGRATION_MESSAGE	?=

PYTHON = ${VIRTUAL_ENV}/bin/python
PYTHON_VERSION_FILE = .python-version
PYTHON_INSTALLED_VERSION_FILE=.installed-python-version
PYTHON_VERSION := $(shell cat ${PYTHON_VERSION_FILE})

TEST_FILES ?= importer
TEST_COV_ARGS ?= --cov importer --cov-fail-under  90
TEST_ARGS ?= ${TEST_COV_ARGS}

VIRTUAL_ENV ?= ${PWD}/venv

_PIP_ADDITIONAL_REQUIREMENTS := $(shell cat requirements.txt)

# utils
UID	:= $(shell id -u)

.DEFAULT_GOAL := help

all: init build startserver  ## init and start the local server

# Init
# ----

init: init-venv init-airflow  ## init local environement

init-airflow: init-airflow-dir  ## init airflow (available env var : USER and PASSWORD)
	_AIRFLOW_WWW_USER_USERNAME="$${USER}" _AIRFLOW_WWW_USER_PASSWORD="$${PASSWORD}" docker-compose up airflow-init

init-venv: ${PYTHON} init-pip requirements.dev.txt ${VIRTUAL_ENV}/bin/pip-sync  ## init local virtual env
	${VIRTUAL_ENV}/bin/pip-sync requirements.dev.txt

init-pip: ${PYTHON}
	${PYTHON} -m pip install --upgrade pip==22.0.4


# Utils
# -----

build:  ## Re-build the images (required after requirements modifications)
	docker-compose build

startserver:  ## Start local servers
	docker-compose up --build --detach
	docker-compose restart

migration:
	docker-compose run --rm -u "${UID}" -e HOME=/home/airflow/ alembic-cli revision --autogenerate -m "${MIGRATION_MESSAGE}"

migrate:
	docker-compose run --rm airflow-init

# Testing
# -------

test: test-init test-run  ## Init and run tests

test-run:  ## Run tests
	${AIRFLOW_TEST_ENV} pytest --import-mode importlib ${TEST_ARGS} ${TEST_FILES}

test-init: init-venv test-init-db test-init-variables  ## Init tests

test-init-db:
	${AIRFLOW} db reset --yes

test-init-variables:
	${AIRFLOW} variables import ./importer/settings/default.json
	${AIRFLOW} variables import ./importer/settings/local.json

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
	${PYTHON} -m pip install pip-tools==6.6.0


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

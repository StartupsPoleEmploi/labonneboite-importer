UID	:= $(shell id -u)
TEST_FILES   =
TESTS_PARAM   =
TEST_WATCH_PARAM = --watch


help:
	poetry install --only help
	poetry run mkdocs serve --dev-addr '127.0.0.1:9999'

develop: 
	docker-compose -f docker-compose.yml down \
	&& docker-compose -f docker-compose.yml up --build

setup:
# for linux : https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html#setting-the-right-airflow-user
	mkdir -p airflow/opt/airflow/logs
	echo "AIRFLOW_UID=${UID}" > .env
	mkdir -p testResults
	chmod 777 testResults

setup-test:
	docker-compose -f docker-compose.testing.yml build

tearDown-test:
	docker-compose -f docker-compose.testing.yml down

test: setup setup-test
	$(MAKE) test-run; r=$$?; \
		$(MAKE) tearDown-test; exit $$r

test-watch: 
	$(MAKE) test TESTS_PARAM=${TEST_WATCH_PARAM}

test-run:
	TEST_FILES=${TEST_FILES} TESTS_PARAM=${TESTS_PARAM} docker-compose -f docker-compose.testing.yml run --rm tests

# migration

MIGRATION_MESSAGE	?=
migration:
	docker-compose run --rm -u "${UID}" -e HOME=/home/airflow/ alembic-cli revision --autogenerate -m "${MIGRATION_MESSAGE}"

migrate-down:
	docker-compose run --rm -u "${UID}" -e HOME=/home/airflow/ alembic-cli downgrade -1


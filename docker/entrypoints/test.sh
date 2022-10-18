# /bin/bash
set -e

# init tests
airflow variables import ./importer/settings/default.json
airflow connections add mysql_importer \
    --conn-host ${IMPORTER_MYSQL_HOST:-importer-mysql} \
    --conn-login ${IMPORTER_MYSQL_LOGIN:-importer} \
    --conn-password ${IMPORTER_MYSQL_PASSWORD:-importer} \
    --conn-port ${IMPORTER_MYSQL_PORT:-3306} \
    --conn-schema ${IMPORTER_MYSQL_SCHEMA:-importer} \
    --conn-type mysql
poetry run alembic -c importer/settings/alembic.ini upgrade head

# run the tests

# -- lint
poetry run flake8 importer --output-file flake8.txt || echo "FAILED flake"
poetry run flake8_junit flake8.txt flake8.xml
rm flake8.txt

# -- unit test & coverage
# -- api
poetry run pytest --junitxml=pytest.xml --html=pytest.html
poetry run coverage xml

# -- build package
poetry build

# prepare test results
echo "Moving test results file..."

mkdir -p testResults
chown -R "${AIRFLOW_UID}:0" \
  /sources/testResults
mv *.xml  ./testResults
mv *.html  ./testResults

echo "Done"

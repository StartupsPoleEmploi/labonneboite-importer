# /bin/bash
set -e

# init tests
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

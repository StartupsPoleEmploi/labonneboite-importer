# /bin/bash
set -ex

function runit() {
    set -e
    sudo -u "#${AIRFLOW_UID}" \
      --preserve-env=AIRFLOW_HOME,AIRFLOW__CORE__SQL_ALCHEMY_CONN,AIRFLOW__CELERY__RESULT_BACKEND \
      $(which ${1:-airflow}) ${@:2}
    return $?
}


./docker/entrypoints/init.sh


pushd ./importer
# run the tests
# -- lint
runit poetry run flake8 importer --output-file flake8.txt || echo "FAILED flake"
runit poetry run flake8_junit flake8.txt flake8.xml
rm flake8.txt

# -- unit test & coverage
# -- api
runit poetry run pytest --junitxml=pytest.xml --html=pytest.html
runit poetry run coverage xml

# -- build package
runit poetry build

# prepare test results
echo "Moving test results file..."
mkdir -p testResults
chown -R "${AIRFLOW_UID}:0" \
  /sources/testResults
mv *.xml  ./testResults
mv *.html  ./testResults
echo "Done"
popd
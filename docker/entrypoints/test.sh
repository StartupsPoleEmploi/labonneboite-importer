# /bin/bash

testReturn=1

failed() {
# you cannot make the exit code 0 otherwie you disable the extraction done after the execution of this script
    testReturn=0
    echo "FAILED $1"
}

set -e

# init tests
pip install -r <(poetry export --only dev --format requirements.txt)

airflow variables import ${AIRFLOW_HOME}/settings/default.json;
airflow variables import ${AIRFLOW_HOME}/settings/docker.json;

airflow connections list --conn-id fs_default | grep fs_default > /dev/null \
  || airflow connections add fs_default --conn-type fs

airflow connections list --conn-id mysql_importer | grep mysql_importer > /dev/null \
  && airflow connections delete mysql_importer
airflow connections add mysql_importer \
    --conn-host ${IMPORTER_MYSQL_HOST:-importer-mysql} \
    --conn-login ${IMPORTER_MYSQL_LOGIN:-importer} \
    --conn-password ${IMPORTER_MYSQL_PASSWORD:-importer} \
    --conn-port ${IMPORTER_MYSQL_PORT:-3306} \
    --conn-schema importer \
    --conn-type mysql

airflow connections list --conn-id http_address | grep http_address > /dev/null \
  || airflow connections add http_address --conn-uri https://api-adresse.data.gouv.fr/

alembic -c ${AIRFLOW_HOME}/settings/alembic.ini upgrade head



# run the tests
# -- lint
if ! flake8 --output-file flake8.txt
then
    failed "flake";
    flake8_junit flake8.txt flake8.xml && echo;
    rm flake8.txt;
fi

# -- type checking
if ! mypy --junit-xml ./mypy.xml .
then
    failed "mypy";
fi

# -- unit test & coverage
# -- api
if pytest --junitxml=pytest.xml --cov
then
    coverage xml
else
    failed "pytest"
fi


# prepare test results
echo "Moving test results file..."
mkdir -p testResults
chown -R "${AIRFLOW_UID}:0" ./testResults
mv *.xml  ./testResults

echo "Done"

exit $testReturn

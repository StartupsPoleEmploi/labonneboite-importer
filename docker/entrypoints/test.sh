# /bin/bash

testReturn=0

failed() {
    testReturn=1
    echo "FAILED $1"
}

set -ex

# init tests
airflow db init
airflow variables import ./importer/settings/default.json
airflow connections list --conn-id mysql_importer | grep mysql_importer > /dev/null \
  && airflow connections delete mysql_importer
airflow connections add mysql_importer \
    --conn-host ${IMPORTER_MYSQL_HOST:-importer-mysql} \
    --conn-login ${IMPORTER_MYSQL_LOGIN:-importer} \
    --conn-password ${IMPORTER_MYSQL_PASSWORD:-importer} \
    --conn-port ${IMPORTER_MYSQL_PORT:-3306} \
    --conn-type mysql

# run the tests
# -- lint
if ! poetry run flake8 --output-file flake8.txt
then
    failed "flake";
    poetry run flake8_junit flake8.txt flake8.xml && echo;
    rm flake8.txt;
fi

# -- type checking
# if ! poetry run mypy --junit-xml ./mypy.xml .
# then
#     failed "mypy";
# fi

# -- unit test & coverage
# -- api
if poetry run pytest --junitxml=pytest.xml --cov --html=pytest.html
then
    poetry run coverage xml
else
    failed "pytest"
fi

# -- build package
if ! poetry build
then
    failed "build"
fi

# prepare test results
echo "Moving test results file..."
mkdir -p testResults
chown -R "${AIRFLOW_UID}:0" \
  /sources/testResults
mv *.xml  ./testResults
mv *.html  ./testResults
echo "Done"

exit $testReturn

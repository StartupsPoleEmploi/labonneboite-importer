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

# run the tests
# -- lint
if ! flake8 --output-file flake8.txt
then
    failed "flake";
    flake8_junit flake8.txt flake8.xml && echo;
    rm flake8.txt;
fi

# -- type checking
# if ! mypy --junit-xml ./mypy.xml .
# then
#     failed "mypy";
# fi

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

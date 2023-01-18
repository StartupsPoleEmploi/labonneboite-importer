# /bin/bash

testReturn=0

failed() {
    # you cannot make the exit code 0 otherwie you disable the extraction done after the execution of this script
    testReturn=1
    echo "FAILED $1"
}

watch=0
parseArgs() {
    while test $# -gt 0; do
        case "$1" in
        --watch)
            watch=1
            ;;
        esac
        shift
    done
}

set -e

parseArgs $*

[[ $watch = 1 ]] && echo "Run test in watch mode"

# init tests
pip install --no-cache-dir -r <(poetry export --only dev --format requirements.txt)

# run the tests
# -- lint
if ! flake8 --output-file flake8.txt; then
    failed "flake"
    flake8_junit flake8.txt flake8.xml && echo
    rm flake8.txt
fi

# -- type checking
# if ! mypy --junit-xml ./mypy.xml .
# then
#     failed "mypy";
# fi

# -- unit test & coverage
# -- api
[[ $watch = 0 ]] && if pytest --junitxml=pytest.xml --cov ${TEST_FILES}; then
    coverage xml
else
    failed "pytest"
fi
[[ $watch = 1 ]] && ptw --wait

# prepare test results
echo "Moving test results file..."
mkdir -p testResults
mv -f *.xml ./testResults
echo "Done"

exit $testReturn

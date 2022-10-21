# La bonne boite data importer

The importer job is to recreate from scratch a complete dataset of offices base on a mapping of a SIRET and a score.

## Software architecture

This projet use an [ETL](https://en.wikipedia.org/wiki/Extract,_transform,_load) ([Apache **Airflow**](https://airflow.apache.org/)) to extract data from the different files and other sources, transform them in LBB Offices (_missing ref_) and to load them in the [La bonne boite database](https://github.com/startupsPoleEmploi/labonneboite)

```
    ┌─────────┐    ┌──────────────────┐
───►│  untar  ├───►│  extract_office  │
    └─────────┘    └──────────────────┘
```

## Dependances

- docker-compose >= 1.27
- git (to retrieve lbb-common project from the requirements)
- pg_config (`libpq-dev` / ubuntu)

### dev

- pyenv
  - python3.10 (installé via `make init`)
- lib de dev (ou `devel`)
  - sqlite3 (`libsqlite3-dev`)
  - mysqlclient (`libmysqlclient-dev`)
  - ffi (`libffi-dev`)
- gcc-11 (pour installer compiler python avec la `libffi`)

## Developement

```
make develop
```

access : https://127.0.0.1:8080/ (`HTTP_PORT` may be changed in .env) with creds : airflow / airflow (from `_AIRFLOW_WWW_USER_USERNAME` and `_AIRFLOW_WWW_USER_PASSWORD`)

# Environment variable

| Var name                       | Default               | Note                                                                                                           |
|--------------------------------|-----------------------|----------------------------------------------------------------------------------------------------------------|
| _PIP_ADDITIONAL_REQUIREMENTS   |                       |                                                                                                                |
| INPUT_DIR                      | ./importer/var/input  | directory where the importer file are read                                                                     |
| WORK_DIR                       | ./importer/var/work   | directory where the importer write it results (and temporary files)                                            |
| OUTPUT_DIR                     | ./importer/var/output | directory where the importer write it results (and temporary files)                                            |
| AIRFLOW_UID                    | 50000                 | uid of the airflow user                                                                                        |
| POSTGRES_USER                  | airflow               | airflow database for core and workers                                                                          | 
| POSTGRES_PASSWORD              | airflow               | ...                                                                                                            |
| IMPORTER_MYSQL_HOST            | importer-mysql        | db info of the importer database                                                                               |
| IMPORTER_MYSQL_PORT            | 3306                  | ...                                                                                                            |
| IMPORTER_MYSQL_ROOT_PASSWORD   | importer              | ...                                                                                                            |
| IMPORTER_MYSQL_PASSWORD        | importer              | ...                                                                                                            |
| IMPORTER_MYSQL_LOGIN           | importer              | ...                                                                                                            |
| HTTP_PORT                      | 8080                  | public HTTP port of the airflow webserver                                                                      |
| FLOWER_HTTP_PORT               | 5555                  | public HTTP port of FLower : the Celery monitoring tool                                                        |
| ENV_TYPE                       | production            | -                                                                                                              |
| _AIRFLOW_WWW_USER_USERNAME     | airflow               | Only used on the 1st init                                                                                      |
| _AIRFLOW_WWW_USER_PASSWORD     | airflow               | Only used on the 1st init                                                                                      |
| AIRFLOW__WEBSERVER__SECRET_KEY | supersecret           | See [airflow config](https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html#secret-key) |

# Run project

See deploy function in the [.execute shell script](./.execute.sh#L70)

## Testing

```
make test
```
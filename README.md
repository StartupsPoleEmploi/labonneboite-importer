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

### dev

- pyenv
  - python3.8.13 (installé via `make init`)
- lib de dev (ou `devel`)
  - sqlite3 (`libsqlite3-dev`)
  - mysqlclient (`libmysqlclient-dev`)
  - ffi (`libffi-dev`)
- gcc-11 (pour installer compiler python avec la `libffi`)
- pg_config (`libpq-dev` / ubuntu)

## Developement

init local env :

```
make init
```

If the init fail you may have to rebuild all without condition:

```
make init --always-make
```

start local env :

```
make startserver
```

access : https://127.0.0.1/ (HTTP_PORT may be changed in .env)

# Environment variable

| Var name                      | Default                | Note                                                                |
|-------------------------------|------------------------|---------------------------------------------------------------------|
| _PIP_ADDITIONAL_REQUIREMENTS  |                        |                                                                     |
| INPUT_DIR                     | ./importer/var/input   | directory where the importer file are read                          |
| OUTPUT_DIR                    | ./importer/var/output  | directory where the importer write it results (and temporary files) |
| AIRFLOW_UID                   | 50000                  | uid of the airflow user                                             |
| IMPORTER_MYSQL_SCHEMA         | importer               | db info of the importer database                                    |
| IMPORTER_MYSQL_ROOT_PASSWORD  | importer               | ...                                                                 |
| IMPORTER_MYSQL_PASSWORD       | importer               | ...                                                                 |
| IMPORTER_MYSQL_LOGIN          | importer               | ...                                                                 |
| HTTP_PORT                     | 80                     | public HTTP port of the airflow webserver                           |
| FLOWER_HTTP_PORT              | 5555                   | public HTTP port of FLower : the Celery monitoring tool             |
| ENV_TYPE                      | production             | -                                                                   |
| _AIRFLOW_WWW_USER_USERNAME    | airflow                | Only used on the 1st init                                           |
| _AIRFLOW_WWW_USER_PASSWORD    | airflow                | Only used on the 1st init                                           |

# Run project

See deploy function in the .execute shell script

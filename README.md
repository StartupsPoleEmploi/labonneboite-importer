# La bonne boite data importer

The importer job is to recreate from scratch a complete dataset of offices base on a mapping of a SIRET and a score.

## Software architecture

This projet use an [ETL](https://en.wikipedia.org/wiki/Extract,_transform,_load) ([Apache **Airflow**](https://airflow.apache.org/)) to extract data from the different files and other sources, transform them in LBB Offices (_missing ref_) and to load them in the [La bonne boite database](https://github.com/startupsPoleEmploi/labonneboite)

```
⟥ load_etablissements ⟶ geocode ⤵
                                 ⟼
⟥          load_scores          ⤴
```

## Dependances

- docker-compose
- htpasswd

### dev

- pyenv
  - python3.8.13 (installé via `make init`)
- lib de dev (ou `devel`)
  - sqlite3 (`libsqlite3-dev`)
  - mysqlclient (`libmysqlclient-dev`)
  - ffi (`libffi-dev`)
- gcc-11 (pour installer compiler python avec la `libffi`)

## Developement

init local env :

```
make init
```

start local env :

```
make startserver
```

access : https://127.0.0.1/ (HTTP_PORT may be changed in .env)

# La bonne boite data importer

## About

The importer job is to recreate from scratch a complete dataset of offices base on a mapping of a SIRET and a score.


## How tos

### Running locally

```
make develop

```

access : https://127.0.0.1:8080/ (`HTTP_PORT` may be changed in .env) with creds : airflow / airflow (from `_AIRFLOW_WWW_USER_USERNAME` and `_AIRFLOW_WWW_USER_PASSWORD`)

### Documentation

The documentation is based on [mkdocs](https://www.mkdocs.org/)

To open the docs:

```
make help
```

It will be accessible [here](http://127.0.0.1:9999/)
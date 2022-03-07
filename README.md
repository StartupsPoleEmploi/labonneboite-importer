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

- python3.8

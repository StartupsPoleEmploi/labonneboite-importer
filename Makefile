init: init-airflow

init-airflow: init-airflow-dir init-airflow-dotenv init-airflow-basic-auth
	docker-compose up airflow-init

init-airflow-dotenv:
	echo "AIRFLOW_UID=$(shell id -u)" >> .env

init-airflow-dir:
	mkdir -p ./dags ./logs ./importer

init-airflow-basic-auth:
	htpasswd -c nginx/etc/nginx/auth/.htpasswd ${USER}

startserver:
	docker-compose up --detach

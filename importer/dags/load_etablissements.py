import datetime

from airflow.operators.dummy import DummyOperator

from airflow import DAG

default_args = {
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": datetime.timedelta(hours=5),
}

with DAG("load-etablissements-2022-03",
         default_args=default_args,
         start_date=datetime.datetime(2022, 3, 1),
         catchup=False,
         schedule_interval="@daily") as dag:
    start_task = DummyOperator(task_id="start")
    end_task = DummyOperator(task_id="end")


start_task \
    >> end_task

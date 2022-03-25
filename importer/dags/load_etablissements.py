import datetime
import os

from airflow.models import Variable
from airflow.operators.dummy import DummyOperator
from airflow.sensors.filesystem import FileSensor

from airflow import DAG

from operators.find_last_file import FindLastFileOperator
from operators.tarfile import UntarOperator

default_args = {
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": datetime.timedelta(hours=5),
}

data_path = Variable.get('data_path')
filepath = os.path.join(data_path, Variable.get('etab_file_glob'))
working_tmp_dir = os.path.join(data_path, 'tmp', "{{ts_nodash}}")

with DAG("load-etablissements-2022-03",
         default_args=default_args,
         start_date=datetime.datetime(2022, 3, 1),
         catchup=False,
         schedule_interval="@daily") as dag:
    start_task = DummyOperator(task_id="start")
    sensor_task = FileSensor(
        task_id="file_sensor_task",
        retries=10,
        retry_delay=1 if os.getenv('ENV_TYPE', default='production') == 'developpement' else 30,
        filepath=filepath,
    )
    find_last_file = FindLastFileOperator(task_id='find_last_tar', filepath=filepath)
    untar_last_file = UntarOperator(
        task_id='untar_last_tar',
        source_path="{{ task_instance.xcom_pull(task_ids='find_last_tar', key='return_value') }}",
        dest_path=working_tmp_dir)
    end_task = DummyOperator(task_id="end")


start_task \
    >> sensor_task \
    >> find_last_file \
    >> untar_last_file \
    >> end_task

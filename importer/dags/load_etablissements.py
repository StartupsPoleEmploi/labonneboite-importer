import datetime
import os
from pathlib import Path

from airflow import DAG
from airflow.models.variable import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.sensors.filesystem import FileSensor

from operators.extract_offices import ExtractOfficesOperator
from operators.find_last_file import FindLastFileOperator
from operators.tarfile import UntarOperator

default_args = {
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": datetime.timedelta(hours=5),
}

data_path = Path(Variable.get('data_path', default_var='/var/input'))
output_path = Path(Variable.get('work_path', default_var='/var/output'))
filepath = data_path / Variable.get('etab_file_glob')
working_tmp_dir = output_path / 'tmp' / "{{ts_nodash}}"
offices_path = working_tmp_dir / "etablissements" / "etablissements.csv"

with DAG("load-etablissements-2022-03",
         default_args=default_args,
         start_date=datetime.datetime(2022, 3, 1),
         catchup=False,
         schedule_interval="@daily") as dag:
    start_task = DummyOperator(task_id="start")
    sensor_task = FileSensor(  # type: ignore [no-untyped-call]
        task_id="file_sensor_task",
        retries=10,
        retry_delay=1 if os.getenv('ENV_TYPE', default='production') == 'development' else 30,
        filepath=filepath,
    )
    find_last_file = FindLastFileOperator(
        task_id='find_last_tar',
        filepath=filepath
    )
    untar_last_file = UntarOperator(
        task_id='untar_last_tar',
        source_path="{{ task_instance.xcom_pull(task_ids='find_last_tar', key='return_value') }}",
        dest_path=working_tmp_dir
    )

    office_path_sensor_task = FileSensor(  # type: ignore [no-untyped-call]
        task_id="office_path_sensor_task",
        retries=0,
        filepath=str(offices_path),
    )
    extract_offices = ExtractOfficesOperator(
        task_id='extract_offices',
        destination_table='etablissements_raw',
        offices_filename=str(offices_path),
    )

    rmdir = BashOperator(
        task_id='delete_result_directory',
        bash_command='rm -r ${WORKING_TMP_DIR}',
        env={'WORKING_TMP_DIR': str(working_tmp_dir)}
    )
    end_task = DummyOperator(task_id="end")

start_task \
>> sensor_task \
>> find_last_file \
>> untar_last_file \
>> office_path_sensor_task \
>> extract_offices \
 \
>> rmdir \
>> end_task

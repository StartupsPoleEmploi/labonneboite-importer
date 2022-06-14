import datetime
from pathlib import Path

from airflow import DAG
from airflow.models.variable import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

from operators.extract_offices import ExtractOfficesOperator
from operators.extract_scores import ExtractScoresOperator
from operators.find_last_file import FindLastFileOperator
from operators.tarfile import UntarOperator

default_args = {
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": datetime.timedelta(hours=5),
}

fs_hook_path = Path('/{{ conn.fs_default.schema }}')
data_path = fs_hook_path / Variable.get('data_path', default_var='/var/input')
output_path = fs_hook_path / Variable.get('work_path', default_var='/var/output')
filepath = data_path / Variable.get('etab_file_glob')
working_tmp_dir = output_path / 'tmp' / "{{ts_nodash}}"
offices_path = working_tmp_dir / "etablissements" / "etablissements.csv"
scores_path = working_tmp_dir / "inference" / "predictions" / "predictions.csv"

with DAG("load-etablissements-2022-04",
         default_args=default_args,
         start_date=datetime.datetime(2022, 4, 16),
         catchup=False,
         schedule_interval="0 3 15 * *") as dag:
    start_task = DummyOperator(task_id="start")
    make_tmp_dir = BashOperator(
        task_id='make_tmp_dir',
        bash_command="""
            mkdir -p "${DIR}" && \
            test -d "${DIR}"
        """,
        env={"DIR": str(working_tmp_dir)})

    with TaskGroup("untar") as untar_group:
        find_last_file = FindLastFileOperator(
            task_id='find_last_tar',
            filepath=filepath
        )
        copy_last_file_locally = BashOperator(
            task_id='copy_last_file_locally',
            bash_command='rsync -h --progress "${FROM}" "${TO}"',
            env={
                'FROM': "{{ task_instance.xcom_pull(task_ids='" + find_last_file.task_id + "') }}",
                'TO': str(working_tmp_dir / 'source.tar')
            })
        untar_last_file = UntarOperator(
            task_id='untar_last_tar',
            source_path=working_tmp_dir / 'source.tar',
            dest_path=working_tmp_dir
        )

        find_last_file >> copy_last_file_locally >> untar_last_file

    with TaskGroup("offices") as offices_group:
        office_path_sensor_task = FileSensor(  # type: ignore [no-untyped-call]
            task_id="office_path_sensor_task",
            retries=0,
            filepath=str(offices_path),
            doc="Check if the offices csv file is set"
        )
        extract_offices = ExtractOfficesOperator(
            task_id='extract_offices',
            destination_table='etablissements_raw',
            offices_filename=str(offices_path),
        )
        office_path_sensor_task >> extract_offices

    with TaskGroup("scores") as scores_group:
        score_path_sensor_task = FileSensor(  # type: ignore [no-untyped-call]
            task_id="scores_path_sensor_task",
            retries=0,
            filepath=str(scores_path),
            doc="Check if the score csv file is set"
        )
        extract_scores_task = ExtractScoresOperator(
            task_id="extract_scores",
            destination_table='etablissements_raw',
            scores_filename=str(scores_path),
        )
        score_path_sensor_task >> extract_scores_task

    retrieve_geoloc_task = DummyOperator(task_id="retrieve_geoloc")

    join = DummyOperator(
        task_id='join_operations',
        trigger_rule=TriggerRule.NONE_FAILED,
    )
    rmdir = BashOperator(
        task_id='delete_result_directory',
        bash_command='rm -r ${WORKING_TMP_DIR}',
        env={'WORKING_TMP_DIR': str(working_tmp_dir)}
    )
    end_task = DummyOperator(task_id="end")

untar_group << [start_task, make_tmp_dir]

untar_group >> offices_group >> join
untar_group >> scores_group >> join
untar_group >> retrieve_geoloc_task >> join

join >> rmdir >> end_task

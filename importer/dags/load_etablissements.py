import datetime
from pathlib import Path
from typing import Optional

from airflow.models.variable import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule
from airflow import DAG

from operators.api_adresse import RetrieveAddressesOperator
from operators.extract_offices import ExtractOfficesOperator
from operators.extract_scores import ExtractScoresOperator
from operators.find_last_file import FindLastFileOperator

default_args = {
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": datetime.timedelta(hours=5),
}

fs_hook_path = Path('/{{ conn.fs_default.schema }}')
data_path = fs_hook_path / Variable.get('data_path', default_var='/var/input')
work_path = fs_hook_path / Variable.get('work_path', default_var='/var/work')
output_path = fs_hook_path / Variable.get('output_path', default_var='/var/output')
max_lines_to_treat: Optional[int] = Variable.get('max_lines_to_treat', default_var=None, deserialize_json=True)
if not isinstance(max_lines_to_treat, int):
    max_lines_to_treat = None

filepath = data_path / Variable.get('etab_file_glob')
working_tmp_dir = work_path / 'tmp' / "{{ ts_nodash }}"
offices_path = str(working_tmp_dir / "etablissements" / "etablissements.csv")
scores_path = str(working_tmp_dir / "inference" / "predictions" / "predictions.csv")
timestamp = '{{ dag_run.logical_date.strftime("%Y_%m_%d_%H%M") }}'
sql_name = f'export_etablissement_backup_{timestamp}.sql.gz'
tar_gz_name = f'{timestamp}.tar.bz2'
last_dump_path = str(output_path / 'latest_data.tar.bz2')

with DAG("load-etablissements-2022-04",
         default_args=default_args,
         start_date=datetime.datetime(2022, 4, 16),
         catchup=False,
         schedule_interval="0 3 15 * *") as dag:
    start_task = DummyOperator(task_id="start")
    make_tmp_dir = BashOperator(task_id='make_tmp_dir',
                                bash_command="""
            mkdir -p "${DIR}" && \
            test -d "${DIR}"
        """,
                                env={"DIR": str(working_tmp_dir)})

    with TaskGroup("untar") as untar_group:
        find_last_file = FindLastFileOperator(task_id='find_last_tar', filepath=filepath)
        copy_last_file_env = {
            'FROM': "{{ task_instance.xcom_pull(task_ids='" + find_last_file.task_id + "') }}",
            'TO': str(working_tmp_dir / 'source.tar.gz')
        }
        copy_last_file_locally = BashOperator(task_id='copy_last_file_locally',
                                              bash_command='rsync -h --progress "${FROM}" "${TO}"',
                                              env=copy_last_file_env)
        untar_last_file = BashOperator(task_id='untar_last_tar',
                                       bash_command='tar -xf "${source_path}" -C "${dest_path}"',
                                       env=dict(
                                           source_path=str(working_tmp_dir / 'source.tar.gz'),
                                           dest_path=str(working_tmp_dir),
                                       ))

        find_last_file >> copy_last_file_locally >> untar_last_file

    with TaskGroup("offices") as offices_group:
        office_path_sensor_task = FileSensor(  # type: ignore [no-untyped-call]
            task_id="office_path_sensor_task",
            retries=0,
            filepath=offices_path,
            doc="Check if the offices csv file is set")
        extract_offices = ExtractOfficesOperator(
            task_id='extract_offices',
            destination_table='etablissements_raw',
            offices_filename=offices_path,
            max_lines_to_treat=max_lines_to_treat,
        )
        office_path_sensor_task >> extract_offices

    with TaskGroup("scores") as scores_group:
        score_path_sensor_task = FileSensor(  # type: ignore [no-untyped-call]
            task_id="scores_path_sensor_task",
            retries=0,
            filepath=scores_path,
            doc="Check if the score csv file is set")
        extract_scores_task = ExtractScoresOperator(
            task_id="extract_scores",
            destination_table='etablissements_raw',
            hiring_filename=scores_path,
            max_lines_to_treat=max_lines_to_treat,
        )
        score_path_sensor_task >> extract_scores_task

    retrieve_geoloc_task = RetrieveAddressesOperator(task_id="retrieve_geoloc",
                                                     source_table='etablissements_raw',
                                                     mysql_conn_id='mysql_importer',
                                                     http_conn_id='http_address')

    join = DummyOperator(
        task_id='join_operations',
        trigger_rule=TriggerRule.NONE_FAILED,
    )
    dump_bash_command = ('mysqldump'
                         '    -u "${DB_USER}"'
                         '    -p"${DB_PASSWORD}"'
                         '    --host ${DB_HOST}'
                         '    --port ${DB_PORT}'
                         '    --column-statistics=0'
                         '    ${DB_NAME} ${TABLE} '
                         "  | sed 's/`${TABLE}`/`%s`/g'"
                         '  | gzip > "${DUMP_PATH}"')
    dump = BashOperator(task_id='dump_sql',
                        bash_command=dump_bash_command,
                        env={
                            "DB_USER": '{{ conn.mysql_importer.login }}',
                            "DB_PASSWORD": '{{ conn.mysql_importer.password }}',
                            "DB_HOST": '{{ conn.mysql_importer.host }}',
                            "DB_PORT": '{{ conn.mysql_importer.port }}',
                            "DB_NAME": '{{ conn.mysql_importer.schema }}',
                            "TABLE": 'etablissements_raw',
                            "DEST_TABLE": 'etablissements_new',
                            "DUMP_PATH": str(output_path / sql_name),
                        })
    make_archive = BashOperator(task_id='make_archive',
                                bash_command='tar -jcvf "${tar_gz_path}" -C "${output_path}" "${sql_name}"',
                                env={
                                    'tar_gz_path': str(output_path / tar_gz_name),
                                    'output_path': str(output_path),
                                    'sql_name': sql_name,
                                })
    make_link_file_to_new_archive_bash_command = ('cd "${OUTPUT_PATH}"'
                                                  '  && ln -fs "${DUMP_PATH}" "${LAST_DUMP_PATH}"'
                                                  '  || cp "${DUMP_PATH}" "${LAST_DUMP_PATH}"')
    make_link_file_to_new_archive = BashOperator(task_id='make_link_file_to_new_archive',
                                                 bash_command=make_link_file_to_new_archive_bash_command,
                                                 env={
                                                     'OUTPUT_PATH': str(output_path),
                                                     'DUMP_PATH': tar_gz_name,
                                                     'LAST_DUMP_PATH': last_dump_path
                                                 })
    rmdir = BashOperator(task_id='delete_result_directory',
                         bash_command='rm -r "${WORKING_TMP_DIR}"',
                         env={
                             'WORKING_TMP_DIR': str(working_tmp_dir),
                         })
    end_task = DummyOperator(task_id="end")

start_task >> make_tmp_dir >> untar_group

untar_group >> offices_group >> retrieve_geoloc_task >> join
untar_group >> scores_group >> join

join >> dump >> make_archive >> make_link_file_to_new_archive >> rmdir >> end_task

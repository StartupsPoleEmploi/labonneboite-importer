from typing import Any, Dict, List, Optional, TypedDict, TYPE_CHECKING

from pendulum import DateTime

from airflow.configuration import AirflowConfigParser
from airflow.models import BaseOperator, DAG, DagRun, TaskInstance

if TYPE_CHECKING:
    import types

    class ContextVar(TypedDict):
        json: Optional[Dict]
        value: Optional[Any]

    class Context(TypedDict):
        conf: AirflowConfigParser
        """
        The full configuration object located at
            airflow.configuration.conf which represents the content of your
            `airflow.cfg`.
        """
        dag: DAG
        """
        The DAG object.
        """
        dag_run: DagRun
        """
        A reference to the DagRun object.
        """
        data_interval_end: DateTime
        """End of the data interval (pendulum.DateTime)."""
        data_interval_start: DateTime
        """Start of the data interval (pendulum.DateTime)."""
        ds: str
        """
        The DAG run’s logical date as YYYY-MM-DD. Same as
            `{{ dag_run.logical_date | ds }}.`

        example

            '2022-03-14'
        """
        ds_nodash: str
        """
        Same as `{{ dag_run.logical_date | ds_nodash }}`.

        @example:

            '20220314'
        """
        execution_date: DateTime
        """
        @deprecated: use data_interval_start or logical_date

        the execution date (logical date), same as `dag_run.logical_date`
        """
        inlets: List
        logical_date: DateTime
        """
        the execution date (logical date), same as `dag_run.logical_date`
        """
        macros: types.ModuleType
        """
        A reference to the macros package, described below.
        """
        next_ds: Optional[str]
        """
        @deprecated: use {{ data_interval_end | ds }}

        the next execution date as YYYY-MM-DD if exists, else None
        @example:

            '2022-03-14'
        """
        next_ds_nodash: Optional[str]
        """
        @deprecated: use {{ data_interval_end | ds_nodash }}

        the next execution date as YYYYMMDD if exists, else None
        @example:

            '20220314'
        """
        next_execution_date: DateTime
        """
        @deprecated: use data_interval_end

        the next execution date (if available) (`pendulum.DateTime`) if
            `{{ execution_date }}` is `2018-01-01 00:00:00` and `schedule_interval`
            is `@weekly`, `{{ next_execution_date }}` will be `2018-01-08 00:00:00`
        """
        outlets: List
        params: Dict
        """
        A reference to the user-defined params dictionary which can
            be overridden by the dictionary passed through trigger_dag -c if you
            enabled dag_run_conf_overrides_params in airflow.cfg.
        """
        prev_data_interval_start_success: Optional[DateTime]
        """
        Start of the data interval from prior successful DAG run
        (`pendulum.DateTime` or `None`).
        """
        prev_data_interval_end_success: Optional[DateTime]
        """
        End of the data interval from prior successful DAG run (pendulum.DateTime or None).
        """
        prev_ds: str
        """
        @deprecated

        the previous execution date as `YYYY-MM-DD` if exists, else `None`

        @example:

            '2022-03-14'
        """
        prev_ds_nodash: str
        """
        @deprecated

        the previous execution date as YYYYMMDD if exists, else None

        @example:

            '20220314'
        """
        prev_execution_date: DateTime
        """
        @deprecated

        the previous execution date (if available) (`pendulum.DateTime`)

        @example: if `{{ execution_date }}` is `2018-01-08 00:00:00` and
            `schedule_interval` is `@weekly`, `{{ prev_execution_date }}` will be
            `2018-01-01 00:00:00`
        """
        prev_execution_date_success: Optional[DateTime]
        """
        @deprecated: use prev_data_interval_start_success

        execution date from prior successful dag run
        """
        prev_start_date_success: Optional[DateTime]
        """
        Start date from prior successful dag run (if available)
        (`pendulum.DateTime` or None).
        """
        run_id: str
        """
        The run_id of the current DAG run.

        @example:

            'manual__2022-03-14T13:31:31.948872+00:00'
        """
        task: BaseOperator
        """
        The Task object.
        """
        task_instance: TaskInstance
        """
        The task_instance object.
        """
        task_instance_key_str: str
        """
        A unique, human-readable key to the task
            instance formatted {dag_id}__{task_id}__{ds_nodash}.
        @example:

            'load-etablissements-2022-03__store_last_in_db_task2__20220314'
        """
        test_mode: bool
        """
        Whether the task instance was called using the CLI’s
            test subcommand.
        """
        ti: TaskInstance
        """
        Same as `{{ task_instance }}`.
        """
        tomorrow_ds: str
        """
        @deprecated

        The day after the execution date as YYYY-MM-DD

        @example:

            '2022-03-15'
        """
        tomorrow_ds_nodash: str
        """
        @deprecated

        the day after the execution date as YYYYMMDD

        @example:

            '20220315'
        """
        ts: str
        """
        Same as `{{ dag_run.logical_date | ts }}`.

        @example:

            '2022-03-14T13:31:31.948872+00:00'
        """
        ts_nodash: str
        """
        Same as `{{ dag_run.logical_date | ts_nodash }}`.
        @example:

            '20180101T000000.'
        """
        ts_nodash_with_tz: str
        """
        Same as `{{ dag_run.logical_date | ts_nodash_with_tz }}`.

        @example:

            '20220314T133131.948872+0000'
        """
        var: ContextVar
        """
        Global defined variables represented as a dictionary. With
            deserialized JSON object, append the path to the key within the JSON
            object.
        """
        conn: Optional[Dict]
        """
        Connection represented as a dictionary.
        """
        yesterday_ds: str
        """
        @deprecated

        the day before the execution date as `YYYY-MM-DD`

        @example:

            '2022-03-13'
        """
        yesterday_ds_nodash: str
        """
        @deprecated

        the day before the execution date as `YYYYMMDD`

        @example:

            '20220313'
        """
else:
    from airflow.utils.context import Context  # noqa: F401
    ContextVar = dict

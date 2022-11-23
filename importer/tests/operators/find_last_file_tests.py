import os
from os.path import join
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, Mock

from operators.find_last_file import FindLastFileOperator

from airflow.exceptions import AirflowSkipException
from airflow.hooks.filesystem import FSHook
from airflow.models.dag import DAG
from common.custom_types import Context
from pendulum import DateTime, UTC  # type: ignore
from datetime import timedelta

DATE_BEFORE_START = DateTime(2020, 1, 15, 2, 0, 0, tzinfo=UTC)
START_DATE = DateTime(2020, 2, 1, 2, 0, 0, tzinfo=UTC)
DATE_BETWEEN_START_AND_LAST_RUN = DateTime(2020, 2, 15, 2, 0, 0, tzinfo=UTC)
LAST_RUN_DATE = DateTime(2020, 3, 1, 2, 0, 0, tzinfo=UTC)
DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN = DateTime(2020, 3, 15, 2, 0, 0, tzinfo=UTC)
CURRENT_RUN_DATE = DateTime(2020, 4, 1, 2, 0, 0, tzinfo=UTC)
DATE_AFTER_START = DateTime(2020, 4, 15, 2, 0, 0, tzinfo=UTC)
NEXT_RUN_DATE = DateTime(2020, 5, 1, 2, 0, 0, tzinfo=UTC)


class TestFindLastFileOperator(TestCase):

    @staticmethod
    def _get_context() -> Context:
        context: Context = Context(prev_data_interval_start_success=START_DATE,
                                   prev_data_interval_end_success=LAST_RUN_DATE,
                                   data_interval_start=LAST_RUN_DATE,
                                   data_interval_end=CURRENT_RUN_DATE,
                                   dag=MagicMock(DAG, start_date=START_DATE))
        return context

    @staticmethod
    def _get_1st_run_context() -> Context:
        context: Context = Context(prev_data_interval_start_success=None,
                                   prev_data_interval_end_success=None,
                                   data_interval_start=START_DATE,
                                   data_interval_end=CURRENT_RUN_DATE,
                                   dag=MagicMock(DAG, start_date=START_DATE))
        return context

    @staticmethod
    def _get_operator(filepath: str) -> FindLastFileOperator:
        mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
        operator = FindLastFileOperator(task_id='test_task_id', filepath=filepath, _fshook=mock_fs_hook)
        return operator

    def test_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as filepath:
            operator = self._get_operator(filepath)
            with self.assertRaises(AirflowSkipException):
                operator.execute(self._get_context())

    @staticmethod
    def touch_file(path: str, datetime: DateTime) -> None:
        add_time = update_time = datetime.timestamp()
        with open(path, 'a'):
            os.utime(path, (add_time, update_time))

    def test_without_files_in_data_interval(self) -> None:
        with tempfile.TemporaryDirectory() as filepath:
            self.touch_file(join(filepath, 'not_matching_glob.csv'), DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN)
            self.touch_file(join(filepath, 'test_before_start.csv'), DATE_BEFORE_START)
            self.touch_file(join(filepath, 'test_before_last_run.csv'), DATE_BETWEEN_START_AND_LAST_RUN)
            self.touch_file(join(filepath, 'test_after.csv'), DATE_AFTER_START)
            operator = self._get_operator(filepath=join(filepath, 'test_*.csv'))
            with self.assertRaises(AirflowSkipException):
                result = operator.execute(self._get_context())
                self.fail(f"shouldn't return : {result}")

    def test_1st_run_without_files_in_data_interval(self) -> None:
        with tempfile.TemporaryDirectory() as filepath:
            self.touch_file(join(filepath, 'not_matching_glob.csv'), DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN)
            self.touch_file(join(filepath, 'test_before_start.csv'), DATE_BEFORE_START)
            self.touch_file(join(filepath, 'test_after.csv'), DATE_AFTER_START)
            operator = self._get_operator(filepath=join(filepath, 'test_*.csv'))

            with self.assertRaises(AirflowSkipException):
                result = operator.execute(self._get_1st_run_context())
                self.fail(f"Shouldn't return : {result}")

    def test_1st_run(self) -> None:
        with tempfile.TemporaryDirectory() as filepath:
            expected_result = join(filepath, 'test_after_start.csv')
            self.touch_file(expected_result, DATE_BETWEEN_START_AND_LAST_RUN)
            operator = self._get_operator(filepath=join(filepath, 'test_*.csv'))

            result = operator.execute(self._get_1st_run_context())

            self.assertEqual(
                expected_result, result,
                'if previous data run is not set (no previous succes) the start date should be use to retrieve the '
                'last file')

    def test(self) -> None:
        with tempfile.TemporaryDirectory() as filepath:
            self.touch_file(join(filepath, 'test_before.csv'), DATE_BETWEEN_START_AND_LAST_RUN)
            self.touch_file(join(filepath, 'test_1.csv'), DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN - timedelta(minutes=1))
            expected_result = join(filepath, 'test_2.csv')
            self.touch_file(expected_result, DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN)
            operator = self._get_operator(filepath=join(filepath, 'test_*.csv'))

            result = operator.execute(self._get_context())

            self.assertEqual(expected_result, result)

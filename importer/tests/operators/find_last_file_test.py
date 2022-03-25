import os
from os.path import join
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, Mock

from operators.find_last_file import FindLastFileOperator

from airflow.exceptions import AirflowFailException
from airflow.configuration import AirflowConfigParser
from airflow.hooks.filesystem import FSHook
from airflow import macros, models
from common.types import Context
from pendulum import DateTime, UTC
from datetime import timedelta

DATE_BEFORE_START = DateTime(2020, 1, 15, 2, 0, 0, tzinfo=UTC)
START_DATE = DateTime(2020, 2, 1, 2, 0, 0, tzinfo=UTC)
DATE_BETWEEN_START_AND_LAST_RUN = DateTime(2020, 2, 15, 2, 0, 0, tzinfo=UTC)
LAST_RUN_DATE = DateTime(2020, 3, 1, 2, 0, 0, tzinfo=UTC)
DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN = DateTime(2020, 3, 15, 2, 0, 0, tzinfo=UTC)
CURRENT_RUN_DATE = DateTime(2020, 4, 1, 2, 0, 0, tzinfo=UTC)
DATE_AFTER_START = DateTime(2020, 4, 15, 2, 0, 0, tzinfo=UTC)
NEXT_RUN_DATE = DateTime(2020, 5, 1, 2, 0, 0, tzinfo=UTC)


class TestUntarOperator(TestCase):

    def _get_context(self, prev_data_interval_success=True) -> Context:
        return {
            "prev_data_interval_start_success": START_DATE,
            "prev_data_interval_end_success": LAST_RUN_DATE,
            "data_interval_start": LAST_RUN_DATE,
            "data_interval_end": CURRENT_RUN_DATE,
            "dag": MagicMock(models.DAG, start_date=START_DATE)
        }

    def _get_1st_run_context(self):
        return {
            "prev_data_interval_start_success": None,
            "prev_data_interval_end_success": None,
            "data_interval_start": START_DATE,
            "data_interval_end": CURRENT_RUN_DATE,
            "dag": MagicMock(models.DAG, start_date=START_DATE)
        }

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as filepath:
            MockFSHook = MagicMock(FSHook, get_path=Mock(return_value="/"))
            dag = MagicMock(models.DAG, start_date=START_DATE)
            operator = FindLastFileOperator(filepath=filepath, _fshook=MockFSHook, task_id='test_task_id')
            with self.assertRaises(AirflowFailException):
                operator.execute(self._get_context())

    def touch_file(self, path: str, datetime: DateTime):
        atime = utime = datetime.timestamp()
        with open(path, 'a'):
            os.utime(path, (atime, utime))

    def test_without_files_in_data_interval(self):
        with tempfile.TemporaryDirectory() as filepath:
            MockFSHook = MagicMock(FSHook, get_path=Mock(return_value="/"))
            self.touch_file(join(filepath, 'not_matching_glob.csv'), DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN)
            self.touch_file(join(filepath, 'test_before_start.csv'), DATE_BEFORE_START)
            self.touch_file(join(filepath, 'test_before_last_run.csv'), DATE_BETWEEN_START_AND_LAST_RUN)
            self.touch_file(join(filepath, 'test_after.csv'), DATE_AFTER_START)
            operator = FindLastFileOperator(task_id="test_operation", filepath=join(filepath, 'test_*.csv'))
            with self.assertRaises(AirflowFailException):
                result = operator.execute(self._get_context())
                self.fail('shouldn\'t return : %r', result)

    def test_1st_run_without_files_in_data_interval(self):
        with tempfile.TemporaryDirectory() as filepath:
            MockFSHook = MagicMock(FSHook, get_path=Mock(return_value="/"))
            self.touch_file(join(filepath, 'not_matching_glob.csv'), DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN)
            self.touch_file(join(filepath, 'test_before_start.csv'), DATE_BEFORE_START)
            self.touch_file(join(filepath, 'test_after.csv'), DATE_AFTER_START)
            operator = FindLastFileOperator(task_id="test_operation", filepath=join(filepath, 'test_*.csv'))

            with self.assertRaises(AirflowFailException):
                result = operator.execute(self._get_1st_run_context())
                self.fail('shouldn\'t return : %r', result)

    def test_1st_run(self):
        with tempfile.TemporaryDirectory() as filepath:
            MockFSHook = MagicMock(FSHook, get_path=Mock(return_value="/"))
            expected_result = join(filepath, 'test_after_start.csv')
            self.touch_file(expected_result, DATE_BETWEEN_START_AND_LAST_RUN)
            operator = FindLastFileOperator(task_id="test_operation", filepath=join(filepath, 'test_*.csv'))

            result = operator.execute(self._get_1st_run_context())

            self.assertEqual(
                expected_result, result,
                'if previous data run is not set (no previous succes) the start date should be use to retrieve the last file'
            )

    def test(self):
        with tempfile.TemporaryDirectory() as filepath:
            MockFSHook = MagicMock(FSHook, get_path=Mock(return_value="/"))
            self.touch_file(join(filepath, 'test_before.csv'), DATE_BETWEEN_START_AND_LAST_RUN)
            self.touch_file(join(filepath, 'test_1.csv'), DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN - timedelta(minutes=1))
            expected_result = join(filepath, 'test_2.csv')
            self.touch_file(expected_result, DATE_BETWEEN_LAST_RUN_AND_CURRENT_RUN)
            operator = FindLastFileOperator(task_id="test_operation", filepath=join(filepath, 'test_*.csv'))

            result = operator.execute(self._get_context())

            self.assertEqual(expected_result, result)

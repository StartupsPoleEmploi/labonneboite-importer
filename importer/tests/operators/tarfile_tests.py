import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, Mock

from common.types import Context
from operators.tarfile import UntarOperator

from airflow.exceptions import AirflowFailException
from airflow.hooks.filesystem import FSHook


class TestUntarOperator(TestCase):

    def test(self) -> None:
        with tempfile.TemporaryDirectory() as dest_path:
            mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
            source_path = os.path.realpath(
                os.path.join(os.path.dirname(__file__), '../data/prod/lbb-output-wf-202202150303.tar'))
            operator = UntarOperator(task_id="test_task",
                                     source_path=source_path,
                                     dest_path=dest_path,
                                     _fshooks={'fs_default': mock_fs_hook})
            operator.execute(Context())

            listdir = os.listdir(dest_path)
            self.assertTrue(listdir)
            self.assertTrue(os.path.exists(os.path.join(dest_path, 'etablissements', 'etablissements.csv')))
            self.assertTrue(os.path.exists(os.path.join(dest_path, 'inference', 'predictions', 'predictions.csv')))

    def test_dir_inexistant_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            dest_path = os.path.join(tempdir, 'subdir')
            mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
            source_path = os.path.realpath(
                os.path.join(os.path.dirname(__file__), '../data/prod/lbb-output-wf-202202150303.tar'))
            operator = UntarOperator(task_id="test_task",
                                     source_path=source_path,
                                     dest_path=dest_path,
                                     _fshooks={'fs_default': mock_fs_hook})

            dest_path_existed = os.path.exists(dest_path)
            operator.execute(Context())

            listdir = os.listdir(dest_path)

            self.assertFalse(dest_path_existed)
            self.assertTrue(os.path.exists(dest_path))
            self.assertEqual(len(listdir), 3)
            self.assertIn('etablissements', listdir)

    def test_invalid_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as dest_path:
            mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
            source_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../data/invalid.tar'))
            operator = UntarOperator(task_id="test_task",
                                     source_path=source_path,
                                     dest_path=dest_path,
                                     _fshooks={'fs_default': mock_fs_hook})
            with self.assertRaises(AirflowFailException):
                operator.execute(Context())

            listdir = os.listdir(dest_path)
            self.assertFalse(listdir)

    def test_invalid_relative_path_with_sep_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as dest_path:
            mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
            source_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../data/invalid.tar'))
            operator = UntarOperator(task_id="test_task",
                                     source_path=source_path,
                                     dest_path=dest_path + os.sep,
                                     _fshooks={'fs_default': mock_fs_hook})
            with self.assertRaises(AirflowFailException):
                operator.execute(Context())

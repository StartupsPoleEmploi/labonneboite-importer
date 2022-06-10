import contextlib
from typing import Any, Iterator
from unittest import TestCase
from unittest.mock import MagicMock, Mock, mock_open, patch

from airflow.hooks.filesystem import FSHook

from operators.extract_scores import ExtractScoresOperator, Rows
from utils.mysql_hook import MySqlHookOnDuplicateKey

EXPECTED_ROW_LENGTH = 7


class ExtractScoresOperatorWithPresetRows(ExtractScoresOperator):
    ROWS = [['123456', '1'], ['234567', '0']]
    TABLE_NAME = 'test_table'

    def __init__(self, *args: Any, **kwargs: Any):
        self.test_mysql_hook = MagicMock(MySqlHookOnDuplicateKey)

        super().__init__(*args, task_id='test', scores_filename='path/test.csv', destination_table=self.TABLE_NAME,
                         _mysql_hook=self.test_mysql_hook, **kwargs)
        self.rows_retrieved = False

    def _open_file(self) -> contextlib.closing:
        return contextlib.closing(Mock())

    def _retrieve_rows_in_file(self, file) -> Rows:
        self.rows_retrieved = True
        return self.ROWS


class ExtractScoresOperatorMysqlTestCase(TestCase):
    def setUp(self) -> None:
        self.operator = ExtractScoresOperatorWithPresetRows()
        self.operator.execute({})

    def assert_called_with_nth_arg(self, arg_number, expected_value):
        self.assertEqual(1, self.operator.test_mysql_hook.insert_rows.call_count)
        self.assertEqual(
            expected_value,
            self.operator.test_mysql_hook.insert_rows.call_args[0][arg_number]
        )

    def test_execute_should_retrieve_rows(self):
        self.assertTrue(self.operator.rows_retrieved)

    def test_execute_should_insert_retrieved_rows_with_default_values(self):
        result_rows = self.operator.test_mysql_hook.insert_rows.call_args[0][1]
        self.assertIsInstance(result_rows, Iterator)
        result_1st_row = next(result_rows)
        self.assertEqual(EXPECTED_ROW_LENGTH, len(result_1st_row))
        self.assertEqual(['123456', '1', '', '', '', '', ''], result_1st_row)

    def test_execute_should_insert_rows_on_the_input_table(self):
        self.assert_called_with_nth_arg(0, ExtractScoresOperatorWithPresetRows.TABLE_NAME)

    def test_execute_should_insert_rows_with_default_values_set(self):
        result_columns = self.operator.test_mysql_hook.insert_rows.call_args[0][2]
        self.assertEqual(EXPECTED_ROW_LENGTH, len(result_columns))
        self.assertIn('raisonsociale', result_columns)
        self.assertIn('codenaf', result_columns)
        self.assertIn('codecommune', result_columns)
        self.assertIn('codepostal', result_columns)
        self.assertIn('departement', result_columns)

    def test_execute_should_insert_rows_on_duplicate_key_update(self):
        call_kwargs = self.operator.test_mysql_hook.insert_rows.call_args[1]
        self.assertIn('on_duplicate_key_update', call_kwargs)
        self.assertIsInstance(call_kwargs['on_duplicate_key_update'], list)
        self.assertIn('score', call_kwargs['on_duplicate_key_update'])


class ExtractScoresOperatorFsHook(ExtractScoresOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_count = 0

    def _insert_rows(self, rows: Rows) -> None:
        self.call_count += 1
        self.last_call_rows = rows


class ExtractScoresOperatorFileSystemTestCase(TestCase):
    def setUp(self) -> None:
        self.fs_hook_mock = MagicMock(FSHook)
        self.fs_hook_mock.get_path = Mock(return_value='/test/')
        self.operator = ExtractScoresOperatorFsHook(task_id='test', _fs_hook=self.fs_hook_mock,
                                                    scores_filename='path/score.csv',
                                                    destination_table='table_name')

    def execute(self, header='siret;predictions', content=""):
        mock: Mock = mock_open(read_data=f'{header}\n{content}')
        with patch('operators.extract_scores.open', mock):
            self.operator.execute({})
        return mock

    def test_execute_should_open(self):
        mock = self.execute()
        mock.assert_called_once()

    def test_execute_should_open_al_file_in_the_fs_hook(self):
        mock = self.execute()
        result_file_path = str(mock.call_args[0][0])
        self.assertTrue(result_file_path.startswith('/test/'))

    def test_execute_without_enough_header_should_fail(self):
        with self.assertRaisesRegex(AssertionError, r'Scores csv should have at least \d+ columns?'):
            self.execute(header="siret")

    def test_execute_without_siret_should_fail(self):
        with self.assertRaisesRegex(AssertionError,
                                    r"Scores csv first row should be the siret \(actually: 'header1'\)"):
            self.execute(header="header1;predictions")

    def test_execute_without_predictions_should_fail(self):
        with self.assertRaisesRegex(AssertionError,
                                    r"Scores csv second row should be the predictions \(actually: 'header2'\)"):
            self.execute(header="siret;header2")

    def test_execute_should_save_the_csv_content(self):
        self.execute(content="1234567;1\n2345678;0\n")
        self.assertEqual(1, self.operator.call_count)
        result_args = self.operator.last_call_rows
        row = next(result_args)
        self.assertEqual(row[0], '1234567')
        self.assertEqual(row[1], '1')

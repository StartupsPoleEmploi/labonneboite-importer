import contextlib
from typing import Any, Iterator, Optional, Iterable, TextIO
from unittest import TestCase
from unittest.mock import MagicMock, Mock, mock_open, patch

from airflow.hooks.filesystem import FSHook

from operators.extract_scores import ExtractScoresOperator, Rows
from utils.mysql_hook import MySqlHookOnDuplicateKey

EXPECTED_ROW_LENGTH = 7


class ExtractScoresOperatorWithPresetRows(ExtractScoresOperator):
    ROWS = [['123456', '1'], ['234567', '0']]
    TABLE_NAME = 'test_table'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.test_mysql_hook = MagicMock(MySqlHookOnDuplicateKey)

        super().__init__(*args, task_id='test', scores_filename='path/test.csv', destination_table=self.TABLE_NAME,
                         _mysql_hook=self.test_mysql_hook, **kwargs)
        self.rows_retrieved = False

    def _open_file(self) -> contextlib.closing[TextIO]:
        return contextlib.closing(Mock())

    def _retrieve_rows_in_file(self, file: Iterable[str]) -> Rows:
        self.rows_retrieved = True
        return iter(self.ROWS)


class ExtractScoresOperatorMysqlTestCase(TestCase):
    def setUp(self) -> None:
        self.operator = ExtractScoresOperatorWithPresetRows()
        self.operator.execute({})

    def assert_called_with_nth_arg(self, arg_number: int, expected_value: Any) -> None:
        self.assertEqual(1, self.operator.test_mysql_hook.insert_rows.call_count)
        self.assertEqual(
            expected_value,
            self.operator.test_mysql_hook.insert_rows.call_args[0][arg_number]
        )

    def test_execute_should_retrieve_rows(self) -> None:
        self.assertTrue(self.operator.rows_retrieved)

    def test_execute_should_insert_retrieved_rows_with_default_values(self) -> None:
        result_rows = self.operator.test_mysql_hook.insert_rows.call_args[0][1]
        self.assertIsInstance(result_rows, Iterator)
        result_1st_row = next(result_rows)
        self.assertEqual(EXPECTED_ROW_LENGTH, len(result_1st_row))
        self.assertEqual(['123456', '1', '', '', '', '', ''], result_1st_row)

    def test_execute_should_insert_rows_on_the_input_table(self) -> None:
        self.assert_called_with_nth_arg(0, ExtractScoresOperatorWithPresetRows.TABLE_NAME)

    def test_execute_should_insert_rows_with_default_values_set(self) -> None:
        result_columns = self.operator.test_mysql_hook.insert_rows.call_args[0][2]
        self.assertEqual(EXPECTED_ROW_LENGTH, len(result_columns))
        self.assertIn('raisonsociale', result_columns)
        self.assertIn('codenaf', result_columns)
        self.assertIn('codecommune', result_columns)
        self.assertIn('codepostal', result_columns)
        self.assertIn('departement', result_columns)

    def test_execute_should_insert_rows_on_duplicate_key_update(self) -> None:
        call_kwargs = self.operator.test_mysql_hook.insert_rows.call_args[1]
        self.assertIn('on_duplicate_key_update', call_kwargs)
        self.assertIsInstance(call_kwargs['on_duplicate_key_update'], list)
        self.assertIn('score', call_kwargs['on_duplicate_key_update'])


class ExtractScoresOperatorFsHook(ExtractScoresOperator):
    def __init__(self,
                 *args: Any,
                 scores_filename: str,
                 destination_table: str,
                 fs_conn_id: str = 'fs_default',
                 db_conn_id: str = 'mysql_importer',
                 chunk_size: int = 100000,
                 _fs_hook: Optional[FSHook] = None,
                 _mysql_hook: Optional[MySqlHookOnDuplicateKey] = None,
                 **kwargs: Any) -> None:
        super().__init__(*args,
                         scores_filename=scores_filename,
                         destination_table=destination_table,
                         fs_conn_id=fs_conn_id,
                         db_conn_id=db_conn_id,
                         chunk_size=chunk_size,
                         _fs_hook=_fs_hook,
                         _mysql_hook=_mysql_hook,
                         **kwargs)
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

    def execute(self, header: str = 'siret;predictions', content: str = "") -> Mock:
        mock: Mock = mock_open(read_data=f'{header}\n{content}')
        with patch('operators.extract_scores.open', mock):
            self.operator.execute({})
        return mock

    def test_execute_should_open(self) -> None:
        mock = self.execute()
        mock.assert_called_once()

    def test_execute_should_open_al_file_in_the_fs_hook(self) -> None:
        mock = self.execute()
        result_file_path = str(mock.call_args[0][0])
        self.assertTrue(result_file_path.startswith('/test/'))

    def test_execute_without_enough_header_should_fail(self) -> None:
        with self.assertRaisesRegex(AssertionError, r'Scores csv should have at least \d+ columns?'):
            self.execute(header="siret")

    def test_execute_without_siret_should_fail(self) -> None:
        with self.assertRaisesRegex(AssertionError,
                                    r"Scores csv first row should be the siret \(actually: 'header1'\)"):
            self.execute(header="header1;predictions")

    def test_execute_without_predictions_should_fail(self) -> None:
        with self.assertRaisesRegex(AssertionError,
                                    r"Scores csv second row should be the predictions \(actually: 'header2'\)"):
            self.execute(header="siret;header2")

    def test_execute_should_save_the_csv_content(self) -> None:
        self.execute(content="1234567;1\n2345678;0\n")
        self.assertEqual(1, self.operator.call_count)
        result_args = self.operator.last_call_rows
        row = next(result_args)
        self.assertEqual(row[0], '1234567')
        self.assertEqual(row[1], '1')

import contextlib
import csv
from pathlib import Path
from typing import Any, Optional, Iterator, List

from airflow.hooks.filesystem import FSHook
from airflow.models import BaseOperator

from utils.csv import SemiColonDialect
from utils.mysql_hook import MySqlHookOnDuplicateKey

Rows = Iterator[List[str]]
RowsWithDefault = Iterator[List[str]]


class ExtractScoresOperator(BaseOperator):
    template_fields = ["scores_filename"]

    def __init__(self,
                 *args: Any,
                 scores_filename: str,
                 destination_table: str,
                 fs_conn_id: str = 'fs_default',
                 db_conn_id: str = 'mysql_importer',
                 chunk_size: int = 100000,
                 _fs_hook: Optional[FSHook] = None,
                 _mysql_hook: Optional[MySqlHookOnDuplicateKey] = None,
                 **kwargs: Any):
        self.scores_filename = scores_filename
        self.destination_table = destination_table
        self.fs_conn_id = fs_conn_id
        self.db_conn_id = db_conn_id
        self.chunk_size = chunk_size
        self._fs_hook = _fs_hook
        self._mysql_hook = _mysql_hook
        super().__init__(*args, **kwargs)

    def _get_mysql_hook(self) -> MySqlHookOnDuplicateKey:
        if not self._mysql_hook:  # pragma: no cover
            self._mysql_hook = MySqlHookOnDuplicateKey(self.db_conn_id)
        return self._mysql_hook

    def execute(self, context: Any) -> None:
        with self._open_file() as file:
            rows = self._retrieve_rows_in_file(file)
            self._insert_rows(rows)

    def _insert_rows(self, rows: Rows) -> None:
        rows_with_default_values: RowsWithDefault = self._map_default_values_to_rows(rows)
        self._insert_rows_with_default_values(rows_with_default_values)

    @staticmethod
    def _map_default_values_to_rows(rows: Rows) -> RowsWithDefault:
        for row in rows:
            yield row + [''] * 5

    def _insert_rows_with_default_values(self, rows_with_dfeault_values) -> None:
        mysql_hook: MySqlHookOnDuplicateKey = self._get_mysql_hook()
        mysql_hook.insert_rows(
            self.destination_table, rows_with_dfeault_values,
            ['siret', 'score', 'raisonsociale', 'codenaf', 'codecommune', 'codepostal', 'departement'],
            on_duplicate_key_update=['score'])

    def _get_file_path(self) -> Path:
        base = self._get_base_path()
        return Path(base) / self.scores_filename

    def _get_base_path(self) -> str:
        fs_hook = self._get_fs_hook()
        return fs_hook.get_path()

    def _get_fs_hook(self) -> FSHook:
        if not self._fs_hook:  # pragma: no cover
            self._fs_hook = FSHook(self.fs_conn_id)
        return self._fs_hook

    def _open_file(self) -> contextlib.closing:
        path = self._get_file_path()
        return self._open_file_path(path)

    def _open_file_path(self, path: Path) -> contextlib.closing:
        file = open(path)
        return contextlib.closing(file)

    @classmethod
    def _retrieve_rows_in_file(cls, file) -> Rows:
        csv_reader = csv.reader(file, SemiColonDialect)
        cls._check_rows_header(csv_reader)
        return csv_reader

    @staticmethod
    def _check_rows_header(csv_reader: Iterator[List[str]]):
        header = next(csv_reader)
        assert len(header) >= 2, "Scores csv should have at least 2 columns"
        assert header[0].lower() == "siret", f"Scores csv first row should be the siret (actually: {header[0]!r})"
        assert header[1].lower() == "predictions", \
            f"Scores csv second row should be the predictions (actually: {header[1]!r})"

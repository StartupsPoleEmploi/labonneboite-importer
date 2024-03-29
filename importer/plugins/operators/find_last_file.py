import glob
import os
from operator import itemgetter
from typing import Iterable, Iterator, Tuple, Optional, Any, Generator

from airflow.exceptions import AirflowSkipException
from airflow.hooks.filesystem import FSHook
from airflow.models.baseoperator import BaseOperator
from pendulum.datetime import DateTime
from pendulum.tz.timezone import UTC

from common.custom_types import Context

TimeIntervale = Tuple[DateTime, DateTime]


class FindLastFileOperator(BaseOperator):
    """
    Find the last modified file during the dag's data interval

    Result will be add in the XCom data.
    """
    template_fields = ["filepath"]

    def __init__(self,
                 *args: Any,
                 filepath: str,
                 fs_conn_id: str = 'fs_default',
                 _fshook: Optional[FSHook] = None,
                 **kwargs: Any):
        self.filepath = filepath
        self.fs_conn_id = fs_conn_id
        self._fshook = _fshook
        super().__init__(*args, **kwargs)

    def _get_fshook(self) -> FSHook:
        if self._fshook is None:  # pragma: no cover
            self._fshook = FSHook(self.fs_conn_id)  # type: ignore [no-untyped-call]
        return self._fshook

    def get_files_to_execute_in_time_intervale(self, time_intervale: TimeIntervale) -> Iterator[Tuple[str, DateTime]]:
        basepath = self._get_fshook().get_path()
        full_path = os.path.join(basepath, self.filepath)
        paths = glob.glob(full_path)
        for path in paths:
            file_modification_ts = os.path.getmtime(path)
            file_modification_dt = DateTime.fromtimestamp(  # type: ignore [no-untyped-call]
                file_modification_ts, tz=UTC)
            if time_intervale[0] <= file_modification_dt < time_intervale[1]:
                print(f"Found {path} modifed on {file_modification_dt}")
                yield path, file_modification_dt

    def get_time_interval(self, context: Context) -> TimeIntervale:
        start = context['data_interval_start'] or context['dag'].start_date
        end = context['data_interval_end']
        return start, end

    def get_files_to_execute(self, context: Context) -> Generator[Tuple[str, DateTime], None, None]:
        time_intervale = self.get_time_interval(context)
        self.log.info("Time interval: from %s to %s", *time_intervale)
        yield from self.get_files_to_execute_in_time_intervale(time_intervale)

    def sort_files(self, files: Iterator[Tuple[str, DateTime]]) -> Iterable[Tuple[str, DateTime]]:
        result = sorted(files, key=itemgetter(1), reverse=True)
        return result

    def find_latest_file(self, files: Iterator[Tuple[str, DateTime]]) -> Tuple[str, DateTime]:
        sorted_files = self.sort_files(files)
        if not sorted_files:
            raise AirflowSkipException('No file found in the interval')
        return next(iter(sorted_files))

    def execute(self, context: Context) -> str:
        files: Iterator[Tuple[str, DateTime]] = self.get_files_to_execute(context)
        file, _ = self.find_latest_file(files)
        return file

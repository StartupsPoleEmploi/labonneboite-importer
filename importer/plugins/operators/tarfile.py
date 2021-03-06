from pathlib import Path
from tarfile import TarFile
from typing import Dict, Optional, Any, Union

from airflow.exceptions import AirflowFailException
from airflow.hooks.filesystem import FSHook
from airflow.models.baseoperator import BaseOperator

from common.types import Context


class BaseTarOperator(BaseOperator):
    _fshooks: Dict[str, FSHook]
    template_fields = ["source_path", "dest_path"]

    def __init__(self,
                 source_path: Union[str, Path],
                 dest_path: Union[str, Path],
                 source_fs_conn_id: str = 'fs_default',
                 dest_fs_conn_id: str = 'fs_default',
                 errorlevel: Optional[int] = None,
                 _fshooks: Optional[Dict[str, FSHook]] = None,
                 **kwargs: Any):
        """
        :params source_path: path of the source directory or tar
        :params dest_path: path of the destination tar or directory
        :params source_fs_conn_id: the file system connection id to use for the source path
        :params dest_fs_conn_id: the file system connection id to use for the destination path
        :params errorlevel: TarFile errorlevel (see:
            [tarfile documentation](https://docs.python.org/3.8/library/tarfile.html#tarfile.TarFile))
        """
        self.source_path = str(source_path)
        self.dest_path = str(dest_path)
        self.source_fs_conn_id = source_fs_conn_id
        self.dest_fs_conn_id = dest_fs_conn_id
        self.errorlevel = errorlevel

        self._fshooks = {} if _fshooks is None else _fshooks
        super().__init__(**kwargs)

    def _get_fshook(self, fs_conn_id: str) -> FSHook:
        """Singleton: get th FSHook from the fs_conn_id."""
        if fs_conn_id not in self._fshooks:  # pragma: no cover
            self._fshooks[fs_conn_id] = FSHook(fs_conn_id)  # type: ignore [no-untyped-call]
        return self._fshooks[fs_conn_id]

    def _get_fs_base_path(self, fs_conn_id: str) -> Path:
        """Get the bash path of the fs_conn_id."""
        fshook = self._get_fshook(fs_conn_id)
        return Path(fshook.get_path())

    def _get_fullpath(self, fs_conn_id: str, subpath: Union[str, Path]) -> Path:
        """Get the full path for a file system connexion and it subpath."""
        base_path = self._get_fs_base_path(fs_conn_id)
        fullpath = base_path / subpath
        return fullpath

    def get_source_fullpath(self) -> Path:
        """Get the full path (with connection) of the source path."""
        fullpath = self._get_fullpath(self.source_fs_conn_id, self.source_path)
        return fullpath

    def get_dest_fullpath(self) -> Path:
        """Get the full path (with connection) of the destination path."""
        fullpath = self._get_fullpath(self.dest_fs_conn_id, self.dest_path)
        return fullpath


class UntarOperator(BaseTarOperator):
    """
    Untar the source_path in the dest_path.
    """

    def is_the_archive_as_relative_path_outside_of_directory(self, archive: TarFile, directory: Path) -> bool:
        absolute_directory = directory.absolute()
        for elementpath in archive.getnames():
            fullpath = absolute_directory / elementpath
            realpath = fullpath.absolute()
            if not realpath.is_relative_to(absolute_directory):
                self.log.error('Invalid path in the archive :', elementpath)
                return True
        return False

    def execute(self, context: Context) -> None:
        self.log.info('Source archive :', self.source_path)
        self.log.info('Dest directory :', self.dest_path)
        source_path = self.get_source_fullpath()
        dest_path = self.get_dest_fullpath()
        tarfile = TarFile(source_path, errorlevel=self.errorlevel)
        tarfile.list()
        if self.is_the_archive_as_relative_path_outside_of_directory(tarfile, dest_path):
            raise AirflowFailException('No relative path is allow in the archive')
        dest_path.mkdir(parents=True, exist_ok=True)
        tarfile.extractall(dest_path)

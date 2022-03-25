import sys
import os
from tarfile import TarFile
from typing import Dict, Optional

from common.types import Context

from airflow.hooks.filesystem import FSHook
from airflow.models import BaseOperator
from airflow.exceptions import AirflowFailException


class BaseTarOperator(BaseOperator):
    _fshooks: Dict[str, FSHook]
    template_fields = ["source_path", "dest_path"]

    def __init__(self,
                 source_path: str,
                 dest_path: str,
                 source_fs_conn_id='fs_default',
                 dest_fs_conn_id='fs_default',
                 errorlevel: Optional[int] = None,
                 _fshooks: Optional[Dict[str, FSHook]] = None,
                 **kwargs):
        """
        :params source_path: path of the source directory or tar
        :params dest_path: path of the destination tar or directory
        :params source_fs_conn_id: the file system connection id to use for the source path
        :params dest_fs_conn_id: the file system connection id to use for the destination path
        :params errorlevel: TarFile errorlevel (see: [tarfile documentation](https://docs.python.org/3.8/library/tarfile.html#tarfile.TarFile))
        """
        self.source_path = source_path
        self.dest_path = dest_path
        self.source_fs_conn_id = source_fs_conn_id
        self.dest_fs_conn_id = dest_fs_conn_id
        self.errorlevel = errorlevel

        self._fshooks = {} if _fshooks is None else _fshooks
        super().__init__(**kwargs)

    def _get_fshook(self, fs_conn_id: str) -> FSHook:
        """Singleton: get th FSHook from the fs_conn_id."""
        if fs_conn_id not in self._fshooks:
            self._fshooks[fs_conn_id] = FSHook(fs_conn_id)  # pragma: no cover
        return self._fshooks[fs_conn_id]

    def _get_fs_base_path(self, fs_conn_id: str) -> str:
        """Get the bash path of the fs_conn_id."""
        fshook = self._get_fshook(self.source_fs_conn_id)
        return fshook.get_path()

    def _get_fullpath(self, fs_conn_id: str, subpath: str) -> str:
        """Get the full path for a file system connexion and it subpath."""
        base_path = self._get_fs_base_path(fs_conn_id)
        fullpath = os.path.join(base_path, subpath)
        return fullpath

    def get_source_fullpath(self) -> str:
        """Get the full path (with connection) of the source path."""
        fullpath = self._get_fullpath(self.source_fs_conn_id, self.source_path)
        return fullpath

    def get_dest_fullpath(self) -> str:
        """Get the full path (with connection) of the destination path."""
        fullpath = self._get_fullpath(self.dest_fs_conn_id, self.dest_path)
        return fullpath


class UntarOperator(BaseTarOperator):
    """
    Untar the source_path in the dest_path.
    """

    @staticmethod
    def directory_with_ending_sep(directory: str) -> str:
        if directory[-1] == os.sep:
            return directory
        else:
            return directory + os.sep

    def is_the_archive_as_relative_path_outside_of_directory(self, archive: TarFile, directory: str):
        directorywithsep = os.path.realpath(self.directory_with_ending_sep(directory))
        for elementpath in archive.getnames():
            fullpath = os.path.join(directorywithsep, elementpath)
            realpath = os.path.realpath(fullpath)
            if not realpath.startswith(directorywithsep):
                self.log.error('Invalid path in the archive :', elementpath)
                return True
        return False

    def execute(self, context: Context):
        self.log.info('Source archive :', self.source_path)
        self.log.info('Dest directory :', self.dest_path)
        source_path = self.get_source_fullpath()
        dest_path = self.get_dest_fullpath()
        tarfile = TarFile(source_path, errorlevel=self.errorlevel)
        tarfile.list()
        if self.is_the_archive_as_relative_path_outside_of_directory(tarfile, dest_path):
            raise AirflowFailException('No relative path is allow in the archive')
        tarfile.extractall(dest_path)

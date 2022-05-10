import csv
import itertools
import os
from typing import Optional, List, Generator, NamedTuple, Dict, Tuple, TYPE_CHECKING, Iterable, Iterator, Any
from typing import Set

from airflow.hooks.filesystem import FSHook
from airflow.models.baseoperator import BaseOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from labonneboite_common.chunk import chunks
from labonneboite_common.departements import DEPARTEMENTS
from labonneboite_common.siret import is_siret

from utils.csv import SemiColonDialect
from utils.get_departement_from_zipcode import get_department_from_zipcode

if TYPE_CHECKING:
    from common.types import Context

# This list contains siret that must not be found in data,
# we use it as a test : if one of those is found in data, we stop the importer
# and need to extract data again

FIELDS = [
    "siret",
    "raisonsociale",
    "enseigne",
    "codenaf",
    "trancheeffectif",
    "numerorue",
    "libellerue",
    "codepostal",
    "tel",
    "email",
    "website",
    "flag_junior",
    "flag_senior",
    "flag_handicap",
    "codecommune",
    "departement",
    "flag_poe_afpr",
    "flag_pmsmp"
]


def add_quote(string: str, quote: str = '"') -> str:
    return quote + string + quote


class Office(NamedTuple):
    siret: str
    raisonsociale: str
    enseigne: str
    codenaf: str
    numerorue: str
    libellerue: str
    codecommune: str
    codepostal: str
    email: str
    tel: str
    trancheeffectif: str
    website: str
    flag_poe_afpr: str
    flag_pmsmp: str
    flag_junior: str
    flag_senior: str
    flag_handicap: str

    @property
    def departement(self) -> Optional[str]:
        return get_department_from_zipcode(self.codepostal)

    def is_valid(self) -> bool:
        return self._check_department() and self._check_siret()

    def _check_department(self) -> bool:
        return self.departement in DEPARTEMENTS

    def _check_siret(self) -> bool:
        return is_siret(self.siret)


class ExtractOfficesOperator(BaseOperator):
    template_fields = ["offices_filename"]

    def __init__(self,
                 *args: Any,
                 offices_filename: str,
                 destination_table: str,
                 fs_conn_id: str = 'fs_default',
                 db_conn_id: str = 'mysql_importer',
                 chunk_size: int = 100000,
                 _fs_hook: Optional[FSHook] = None,
                 _mysql_hook: Optional[MySqlHook] = None,
                 **kwargs: Any
                 ):
        self._input_filename = offices_filename
        self._chunk_size = chunk_size
        self._fs_conn_id = fs_conn_id
        self._fs_hook = _fs_hook
        self._db_conn_id = db_conn_id
        self._mysql_hook = _mysql_hook
        self._table_name = destination_table
        super().__init__(*args, **kwargs)

    def _get_fs_hook(self) -> FSHook:
        if not self._fs_hook:  # pragma: no cover
            self._fs_hook = FSHook(self._fs_conn_id)  # type: ignore [no-untyped-call]
        return self._fs_hook

    def _get_fullpath(self) -> str:
        fshook = self._get_fs_hook()
        base_path = fshook.get_path()
        fullpath = os.path.join(base_path, self._input_filename)
        return fullpath

    def _get_mysql_hook(self) -> MySqlHook:
        if not self._mysql_hook:
            self._mysql_hook = MySqlHook(self._db_conn_id)
        return self._mysql_hook

    def _log_debug(self, existing_set: Set[str], creatable_sirets: Set[str]) -> None:
        self.log.info("nombre d'etablissement dans le csv : %i" % len(creatable_sirets))

        if creatable_sirets:
            self.log.info("liste de 20 sirets dans le csv")
            for siret in itertools.islice(creatable_sirets, 20):
                self.log.info(f" siret : {siret}")

        self.log.info("nombre d'etablissement existant : %i" % len(existing_set))
        if existing_set:
            self.log.info("liste de 20 sirets existant")
            for siret in itertools.islice(existing_set, 20):
                self.log.info(f" siret : {siret}")

    def execute(self, context: 'Context') -> int:
        existing_set = set(self._get_sirets_from_database())
        sirets_inserted: Set[str] = set()

        for offices in self._get_offices_from_file():
            creatable_sirets = set(offices.keys())

            # 1 - create offices which did not exist before
            self._create_update_offices(offices)
            self._log_debug(existing_set, creatable_sirets)

            sirets_inserted = sirets_inserted.union(creatable_sirets)

        # 2 - delete offices which no longer exist
        deletable_sirets = existing_set - sirets_inserted
        self._delete_deletable_offices(deletable_sirets)
        return len(sirets_inserted)

    def _get_sirets_from_database(self) -> List[str]:
        query = f'SELECT "siret" FROM "{self._table_name}"'
        rows: List[Tuple[str]] = self._get_mysql_hook().get_records(query)
        return [row[0] for row in rows if is_siret(row[0])]

    def _create_update_offices(self, csv_offices: Dict[str, Office]) -> None:
        """
        create new offices (that are not yet in our etablissement table)
        """
        self._get_mysql_hook().insert_rows(self._table_name, [
            [
                getattr(office, key) for key in FIELDS
            ]
            for office in csv_offices.values()
        ], FIELDS, replace=True)

    @staticmethod
    def check_fields() -> bool:
        """
        Unsure that all fields are in the Office
        """
        result = all(map(Office._fields.__contains__, FIELDS))
        return result

    def _create_delete_sirets_request(self, sirets: Iterable[str]) -> str:
        comma_separated_sirets = map(add_quote, sirets)
        stringified_sirets = ', '.join(comma_separated_sirets)
        return f'DELETE FROM "{self._table_name}" WHERE "siret" IN ({stringified_sirets})'

    def _delete_deletable_offices(self, deletable_sirets: Set[str]) -> None:
        if deletable_sirets:
            self._get_mysql_hook().run([
                self._create_delete_sirets_request(sirets)
                for sirets in chunks(list(deletable_sirets), self._chunk_size)
            ])
        self.log.info("%i no longer existing offices deleted.", len(deletable_sirets))

    @staticmethod
    def _check_header(header: Dict[str, str]) -> None:
        assert list(header.keys()) == list(header.values()), f"{list(header.keys())} != {list(header.values())}"

    def _read_file(self) -> Generator[Dict[str, str], None, None]:

        with open(self._get_fullpath()) as my_file:
            reader: Iterable[Dict[str, str]] = csv.DictReader(my_file, Office._fields, dialect=SemiColonDialect)
            iterator: Iterator[Dict[str, str]] = iter(reader)
            self._check_header(header=next(iterator))
            yield from iterator

    def _read_offices(self) -> Generator[Office, None, None]:
        for office in self._read_file():
            yield Office(**office)

    def _get_offices_from_file(self) -> Generator[Dict[str, Office], None, None]:
        self.log.info("extracting %s...", self._get_fullpath())
        count = 0
        offices = {}

        office: Office
        for office in self._read_offices():
            if not office.is_valid():
                continue
            count += 1
            offices[office.siret] = office
            if count % self._chunk_size == 0:
                self.log.debug("processed %s lines", count)
                yield offices
                offices = {}
        yield offices

        self.log.info("%i offices total", count)
        self.log.info("finished reading offices...")
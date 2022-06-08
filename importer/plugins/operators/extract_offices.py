import csv
import itertools
from pathlib import Path
from typing import Optional, List, Generator, Dict, Tuple, TYPE_CHECKING, Iterable, Iterator, Any, NamedTuple
from typing import Set

from airflow.hooks.filesystem import FSHook
from airflow.models.baseoperator import BaseOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from labonneboite_common.chunk import chunks
from labonneboite_common.departements import DEPARTEMENTS
from labonneboite_common.siret import is_siret
from sqlalchemy import ColumnDefault

from models import ExportableOffice
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


def is_null(string: str) -> bool:
    return string == 'NULL'


class Office(NamedTuple):
    siret: str
    raisonsociale: Optional[str]
    enseigne: Optional[str]
    codenaf: Optional[str]
    numerorue: Optional[str]
    libellerue: Optional[str]
    codecommune: Optional[str]
    codepostal: Optional[str]
    email: Optional[str]
    tel: Optional[str]
    trancheeffectif: Optional[str]
    website: Optional[str]
    flag_poe_afpr: Optional[str]
    flag_pmsmp: Optional[str]
    flag_junior: Optional[str]
    flag_senior: Optional[str]
    flag_handicap: Optional[str]

    @property
    def departement(self) -> Optional[str]:
        return get_department_from_zipcode(self.codepostal)

    def is_valid(self) -> bool:
        return self._check_department() and self._check_siret()

    @classmethod
    def without_nulls(cls, *args, **kwargs) -> 'Office':
        self = cls(*args, **kwargs)
        new_args: List[Any] = []
        for key, value in zip(cls._fields, self):
            new_args.append(cls._get_default_for_null_value(key, value))
        return cls(*new_args)

    @classmethod
    def _get_default_for_null_value(cls, key, value) -> Optional[Any]:
        if is_null(value):
            return cls._get_default_or_none(key)
        return value

    @classmethod
    def _get_default_or_none(cls, key) -> Optional[Any]:
        default: Optional[ColumnDefault] = ExportableOffice.__table__.columns[key].default
        if default:
            return cls._get_column_default(default)
        return None

    @staticmethod
    def _get_column_default(default: ColumnDefault) -> Any:
        default_value = default.arg
        if default.is_callable:
            default_value = default.arg()
        return default_value

    def _check_department(self) -> bool:
        return self.departement in DEPARTEMENTS

    def _check_siret(self) -> bool:
        return is_siret(self.siret)


class ExtractOfficesOperator(BaseOperator):
    template_fields = ["offices_filename"]
    REST_KEY = None

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
        self.offices_filename = offices_filename
        self.destination_table = destination_table
        self.fs_conn_id = fs_conn_id
        self.db_conn_id = db_conn_id
        self.chunk_size = chunk_size
        self._fs_hook = _fs_hook
        self._mysql_hook = _mysql_hook
        super().__init__(*args, **kwargs)

    def _get_fs_hook(self) -> FSHook:
        if not self._fs_hook:  # pragma: no cover
            self._fs_hook = FSHook(self.fs_conn_id)  # type: ignore [no-untyped-call]
        return self._fs_hook

    def _get_fullpath(self) -> str:
        fshook = self._get_fs_hook()
        base_path = Path(fshook.get_path())
        fullpath = base_path / self.offices_filename
        return str(fullpath)

    def _get_mysql_hook(self) -> MySqlHook:
        if not self._mysql_hook:
            self._mysql_hook = MySqlHook(self.db_conn_id)
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
        query = f'SELECT siret FROM {self.destination_table}'
        rows: List[Tuple[str]] = self._get_mysql_hook().get_records(query)
        return [row[0] for row in rows if is_siret(row[0])]

    def _create_update_offices(self, csv_offices: Dict[str, Office]) -> None:
        """
        create new offices (that are not yet in our etablissement table)
        """
        self._get_mysql_hook().insert_rows(self.destination_table, [
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

    def _create_delete_sirets_sql_request(self, sirets: Iterable[str]) -> str:
        comma_separated_sirets = map(add_quote, sirets)
        stringified_sirets = ', '.join(comma_separated_sirets)
        return f'DELETE FROM "{self.destination_table}" WHERE "siret" IN ({stringified_sirets})'

    def _delete_deletable_offices(self, deletable_sirets: Set[str]) -> None:
        if deletable_sirets:
            self._get_mysql_hook().run([
                self._create_delete_sirets_sql_request(sirets)
                for sirets in chunks(list(deletable_sirets), self.chunk_size)
            ])
        self.log.info("%i no longer existing offices deleted.", len(deletable_sirets))

    @staticmethod
    def _check_header(header: Dict[str, str]) -> None:
        keys = list(header.keys())
        values = list(header.values())
        assert keys == values, f"{keys} != {values} (^{set(map(str, keys)) ^ set(map(str, values))})"

    def _get_dict_reader(self, my_file: Iterable[str]) -> Iterable[Dict[str, str]]:
        reader: Iterable[Dict[str, str]]

        reader = csv.DictReader(
            my_file,
            Office._fields,
            restkey=self.__class__.REST_KEY,
            dialect=SemiColonDialect
        )

        return reader

    def _read_file(self) -> Generator[Dict[str, str], None, None]:
        iterator: Iterator[Dict[str, str]]
        reader: Iterable[Dict[str, str]]

        with open(self._get_fullpath()) as my_file:
            reader = self._get_dict_reader(my_file)
            iterator = iter(reader)
            self._check_header(header=next(iterator))
            yield from iterator

    def _read_offices(self) -> Generator[Office, None, None]:
        for csv_row in self._read_file():
            if self._has_extra_columns(csv_row):
                self.log.error(f"Invalid row for siret: {csv_row['siret']}")
                continue
            office_without_null = Office.without_nulls(**csv_row)
            yield office_without_null

    @classmethod
    def _has_extra_columns(cls, csv_entry: Dict[str, str]) -> bool:
        return cls.REST_KEY in csv_entry

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
            if count % self.chunk_size == 0:
                self.log.debug("processed %s lines", count)
                yield offices
                offices = {}
        yield offices

        self.log.info("%i offices total", count)
        self.log.info("finished reading offices...")

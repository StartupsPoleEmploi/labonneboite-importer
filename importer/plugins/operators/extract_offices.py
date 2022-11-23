import csv
import itertools
from pathlib import Path
from typing import Optional, List, Generator, Dict, Tuple, Iterable, Iterator, Any, NamedTuple, Collection, Text
from typing import Set

import sqlalchemy as sqla
from airflow.hooks.filesystem import FSHook
from airflow.models.baseoperator import BaseOperator
from labonneboite_common.chunk import chunks
from labonneboite_common.departements import DEPARTEMENTS
from labonneboite_common.siret import is_siret
from sqlalchemy import ColumnDefault

from common.custom_types import Context
from models import ExportableOffice
from utils import SemiColonDialect
from utils.get_departement_from_zipcode import get_department_from_zipcode
from utils.mysql_hook import MySqlHookOnDuplicateKey

# This list contains siret that must not be found in data,
# we use it as a test : if one of those is found in data, we stop the importer
# and need to extract data again

FIELDS = [
    "siret", "raisonsociale", "enseigne", "codenaf", "trancheeffectif", "numerorue", "libellerue", "codepostal", "tel",
    "email", "website", "flag_junior", "flag_senior", "flag_handicap", "codecommune", "departement", "flag_poe_afpr",
    "flag_pmsmp"
]

TRANCHEEFFECTIF_MAP = {
    "0-0": "00",
    "1-2": "01",
    "3-5": "02",
    "6-9": "03",
    "10-19": "11",
    "20-49": "12",
    "50-99": "21",
    "100-199": "22",
    "200-249": "31",
    "250-499": "32",
    "500-999": "41",
    "1000-1999": "42",
    "2000-4999": "51",
    "5000-9999": "52",
    "10000+": "53",
}


def add_quote(string: str, quote: str = '"') -> str:
    return quote + string + quote


def is_null(string: Optional[str]) -> bool:
    return string is None or string == 'NULL'


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

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @property
    def errors(self) -> Collection[str]:
        errors = []
        if not self._check_department():
            errors.append("invalid department")
        if not self._check_siret():
            errors.append("invalid siret")
        errors.extend(self._check_fields())
        return errors

    @classmethod
    def without_nulls(cls, siret: str, **kwargs: str) -> 'Office':
        self = cls(siret, **kwargs)
        new_args: List[Optional[str]] = []
        for key, value in zip(cls._fields, self):
            if key != 'siret':
                new_args.append(cls._get_default_for_null_value(key, value))
        return cls(siret, *new_args)

    @classmethod
    def _get_default_for_null_value(cls, key: str, value: Optional[str]) -> Optional[Any]:
        if is_null(value):
            return cls._get_default_or_none(key)
        return value

    @classmethod
    def _get_default_or_none(cls, key: str) -> Optional[Any]:
        assert key in ExportableOffice.__table__.columns
        default: Optional[ColumnDefault] = ExportableOffice.__table__.columns[key].default
        if default:
            return cls._get_column_default(default)
        return None

    @staticmethod
    def _get_column_default(default: ColumnDefault) -> Any:
        default_value = default.arg
        assert not default.is_callable
        return default_value

    def _check_department(self) -> bool:
        return self.departement in DEPARTEMENTS

    def _check_siret(self) -> bool:
        return is_siret(self.siret)

    def _check_fields(self) -> Collection[str]:
        errors: List[str] = []
        for key, value in zip(self._fields, self):
            column = ExportableOffice.__table__.columns[key]
            errors.extend(self._check_field(column, value))
        return errors

    def _check_field(self, column: 'sqla.Column[Any]', value: Optional[str]) -> Collection[str]:
        errors: List[str] = []
        errors.extend(self._check_nullable(column, value))
        if isinstance(column.type, sqla.String):
            errors.extend(self._check_string_field(column, column.type, value))
        return errors

    @staticmethod
    def _check_nullable(column: 'sqla.Column[Any]', value: Optional[Any]) -> Collection[str]:
        errors = []
        if value is None and not column.nullable:
            errors.append(f"invalid {column.key}: column cannot be null")
        return errors

    @staticmethod
    def _check_string_field(column: 'sqla.Column[Text]', column_type: sqla.String,
                            value: Optional[str]) -> Collection[str]:
        if value is None:
            pass
        elif column_type.length is not None and len(value) > column_type.length:
            return [f'invalid {column.key}: data too long for column']
        return []


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
                 _mysql_hook: Optional[MySqlHookOnDuplicateKey] = None,
                 **kwargs: Any):
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

    def _get_mysql_hook(self) -> MySqlHookOnDuplicateKey:
        if not self._mysql_hook:  # pragma: no cover
            self._mysql_hook = MySqlHookOnDuplicateKey(self.db_conn_id)
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

    def execute(self, context: Context) -> int:
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
        self._get_mysql_hook().insert_rows(
            self.destination_table, [[getattr(office, key) for key in FIELDS] for office in csv_offices.values()],
            FIELDS,
            on_duplicate_key_update=True)

    @staticmethod
    def check_fields() -> Tuple[bool, Tuple[str, ...]]:
        """
        Unsure that all fields are in the Office
        """
        success: bool

        missing_fields = tuple(field for field in FIELDS if not hasattr(Office, field))
        success = not bool(missing_fields)
        return success, missing_fields

    def _create_delete_sirets_sql_request(self, sirets: Iterable[str]) -> str:
        comma_separated_sirets = map(add_quote, sirets)
        stringified_sirets = ', '.join(comma_separated_sirets)
        return f'DELETE FROM `{self.destination_table}` WHERE `siret` IN ({stringified_sirets})'

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

        reader = csv.DictReader(my_file, Office._fields, restkey=self.__class__.REST_KEY, dialect=SemiColonDialect)

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
                self.log.error(f"Invalid row for siret {csv_row['siret']} : has extra column")
                continue
            csv_row = self.map_fields(csv_row)
            office_without_null = Office.without_nulls(**csv_row)
            yield office_without_null

    @classmethod
    def map_fields(cls, csv_row: Dict[str, str]) -> Dict[str, str]:
        csv_row['trancheeffectif'] = TRANCHEEFFECTIF_MAP.get(csv_row['trancheeffectif'], csv_row['trancheeffectif'])
        return csv_row

    @classmethod
    def _has_extra_columns(cls, csv_entry: Dict[str, str]) -> bool:
        return cls.REST_KEY in csv_entry

    def _get_offices_from_file(self) -> Generator[Dict[str, Office], None, None]:
        self.log.info("extracting %s...", self._get_fullpath())
        count = 0
        offices = {}

        office: Office
        for office in self._read_offices():
            if not office.is_valid:
                self.log.error(f"Invalid office for siret {office.siret} : {', '.join(office.errors)}")
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

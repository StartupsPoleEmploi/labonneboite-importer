import csv
import io
from collections.abc import Collection
from typing import Optional, Dict, Iterator, Tuple, Generator, Iterable, Any

import requests
from airflow.models.baseoperator import BaseOperator
from airflow.providers.http.hooks.http import HttpHook
from tenacity import retry
from tenacity.stop import stop_after_attempt, stop_after_delay
from tenacity.wait import wait_fixed

from common.types import Context
from utils.codecommune import CODE_COMMUNE
from utils.mysql_hook import MySqlHookOnDuplicateKey

DEFAULT_FIELDS = ['raisonsociale', 'codenaf', 'codecommune', 'codepostal', 'departement']


class InvalidCodeCommune(Exception):
    pass


Addresses = Generator[Dict[str, str], None, None]


class RetrieveAddressesOperator(BaseOperator):
    """
    Find the missing addresses
    """

    def __init__(self,
                 source_table: str,
                 mysql_conn_id: str = MySqlHookOnDuplicateKey.default_conn_name,
                 http_conn_id: str = 'http_address',
                 chunk_size: int = 1000,
                 _mysql_hook: Optional[MySqlHookOnDuplicateKey] = None,
                 _http_hook: Optional[HttpHook] = None,
                 **kwargs: Any):
        super().__init__(**kwargs)
        self.source_table = source_table
        self.chunk_size = chunk_size
        self.mysql_conn_id = mysql_conn_id
        self._mysql_hook = _mysql_hook
        self.http_conn_id = http_conn_id
        self._http_hook = _http_hook

    def execute(self, context: Context) -> None:
        incomplete_addresses = self._retrieve_incomplete_address()
        addresses = self._retrieve_addresses(incomplete_addresses)
        self._insert_addresses(addresses)

    def _filter_invalid_addresses(self, addresses: Addresses) -> Addresses:
        for address in addresses:
            if all(address.values()):
                yield address

    def _retrieve_incomplete_address(self) -> Generator[Dict[str, str], None, None]:
        rows = "siret", "numerorue", "libellerue", "codepostal", "codecommune"
        records = self._retrieve_incomplete_address_records(rows)
        yield from self._format_records_to_incomplete_addresses(rows, records)

    def _retrieve_incomplete_address_records(self, rows: Iterable[str]) -> Iterator[Iterable[str]]:
        mysql_hook = self._get_mysql_hook()
        result: Iterator[list[str]] = mysql_hook.get_records(f"SELECT {', '.join(rows)} FROM {self.source_table} "
                                                             "WHERE coordinates_x IS NULL OR coordinates_y IS NULL")
        return result

    @staticmethod
    def _format_records_to_incomplete_addresses(
            rows: Tuple[str, ...], records: Iterator[Iterable[str]]) -> Generator[Dict[str, str], None, None]:
        for record in records:
            yield dict(zip(rows, record))

    @classmethod
    def _get_full_address(cls, incomplete_address: Dict[str, str]) -> str:
        city = cls._get_commune_name(incomplete_address['codecommune'])
        zipcode = incomplete_address['codepostal']
        street_name, street_number = cls._handle_lieu_dit(street_number=incomplete_address['numerorue'],
                                                          street_name=incomplete_address['libellerue'])
        full_address = f"{street_number} {street_name} {zipcode} {city}"
        return full_address.strip()

    def _retrieve_addresses(self, incomplete_addresses: Iterator[Dict[str, str]]) -> Addresses:
        for string_io in self._generate_api_files(incomplete_addresses):
            addresses = self._retrieve_addresses_from_file(string_io)
            filtered_addresses = self._filter_invalid_addresses(addresses)
            yield from filtered_addresses

    def _generate_api_files(self, incomplete_addresses: Iterator[Dict[str, str]]) -> Generator[io.StringIO, None, None]:
        headers = ["siret", "full_address", "citycode"]
        string_io, writer = self._create_address_api_writer(headers)
        i = 0
        for api_row in self._generate_address_api_rows(incomplete_addresses):
            writer.writerow(api_row)
            i += 1
            if i % self.chunk_size == 0:
                yield string_io
                string_io, writer = self._create_address_api_writer(headers)

        if i % self.chunk_size != 0:
            yield string_io

    def _get_mysql_hook(self) -> MySqlHookOnDuplicateKey:
        if not self._mysql_hook:  # pragma: no cover
            self._mysql_hook = MySqlHookOnDuplicateKey(self.mysql_conn_id)
        return self._mysql_hook

    def _get_http_hook(self) -> HttpHook:
        if not self._http_hook:  # pragma: no cover
            self._http_hook = HttpHook(http_conn_id=self.http_conn_id)
        return self._http_hook

    def _retrieve_addresses_from_file(self, file: io.StringIO) -> Addresses:
        content = file.getvalue().encode('utf-8')
        response = self._retrieve_addresses_from_file_content(content)
        yield from self._read_retrieved_addresses_response(response)

    @retry(stop=stop_after_attempt(10) | stop_after_delay(30), wait=wait_fixed(10))
    def _retrieve_addresses_from_file_content(self, content: bytes) -> requests.Response:
        http_hook = self._get_http_hook()
        response: requests.Response = http_hook.run('/search/csv/',
                                                    files={"data": content},
                                                    params={
                                                        "columns": "full_address",
                                                        "city_code": "city_code",
                                                    })
        return response

    @staticmethod
    def _get_commune_name(codecommune: str) -> str:
        try:
            return CODE_COMMUNE[codecommune]
        except KeyError:
            raise InvalidCodeCommune

    @classmethod
    def _handle_lieu_dit(cls, street_name: str, street_number: str) -> Tuple[str, str]:
        if "LIEU DIT " in street_name:
            street_name = street_name.replace("LIEU DIT ", "")
            street_number = ""
        return street_name, street_number

    @staticmethod
    def _read_retrieved_addresses_response(response: requests.Response) -> Addresses:
        reader = csv.DictReader(io.StringIO(response.text))
        for row in reader:
            yield {
                "siret": row["siret"],
                "coordinates_x": row["longitude"],
                "coordinates_y": row["latitude"],
            }

    @staticmethod
    def _create_address_api_writer(headers: Collection[str]) -> Tuple[io.StringIO, "csv.DictWriter[str]"]:
        string_io = io.StringIO()
        writer = csv.DictWriter(string_io, headers)
        writer.writeheader()
        return string_io, writer

    def _generate_address_api_rows(
            self, incomplete_addresses: Iterator[Dict[str, str]]) -> Generator[Dict[str, str], None, None]:
        for incomplete_address in incomplete_addresses:
            try:
                yield {
                    "siret": incomplete_address['siret'],
                    "full_address": self._get_full_address(incomplete_address),
                    "citycode": incomplete_address['codecommune'],
                }
            except InvalidCodeCommune:
                self.log.warning(f"invalid code commune for siret {incomplete_address['siret']}")
                continue

    def _insert_addresses(self, addresses: Addresses) -> None:
        rows = self._format_rows_to_insert(addresses)
        self._get_mysql_hook().insert_rows(self.source_table,
                                           rows, ['siret', 'coordinates_x', 'coordinates_y'] + DEFAULT_FIELDS,
                                           on_duplicate_key_update=['coordinates_x', 'coordinates_y'])

    @staticmethod
    def _format_rows_to_insert(addresses: Addresses) -> Iterator[Iterable[str]]:
        default_fields = ('',) * len(DEFAULT_FIELDS)
        for address in addresses:
            yield (address['siret'], address['coordinates_x'], address['coordinates_y']) + default_fields

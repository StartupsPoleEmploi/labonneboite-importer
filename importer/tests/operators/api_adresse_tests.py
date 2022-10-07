import csv
import re
from typing import Any, Optional, Union, Generator, Iterator, Iterable
from unittest import TestCase
from unittest.mock import Mock, MagicMock

import requests
from airflow.providers.http.hooks.http import HttpHook

from common.types import Context
from operators.api_adresse import RetrieveAddressesOperator, Addresses
from utils.mysql_hook import MySqlHookOnDuplicateKey


class EmptyRetrieveAddressesOperator(RetrieveAddressesOperator):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(task_id='test', source_table="test", **kwargs)

    def _retrieve_incomplete_address(self) -> Generator[dict[str, str], None, None]:
        self.retrieve_incomplete_address_called = True
        yield {"ok": "_retrieve_incomplete_address"}

    def _retrieve_addresses(self, incomplete_addresses: Iterator[dict[str, str]]) -> Addresses:
        self.retrieved_addresses = list(incomplete_addresses)
        yield {"ok": "_retrieve_addresses"}

    def _insert_addresses(self, addresses: Addresses) -> None:
        self.inserted_addresses = list(addresses)


REQUIRED_ROWS = ['siret', 'numerorue', 'libellerue', 'codepostal', 'codecommune']
TEST_VALUES = ["12345678901234", "1", "rue du test", "75011", "75056"]


def _create_sql_result(siret: str = "12345678901234",
                       numerorue: str = "1",
                       libellerue: str = "rue du test",
                       codepostal: str = "75011",
                       codecommune: str = "75056") -> dict[str, str]:
    return dict(
        siret=siret,
        numerorue=numerorue,
        libellerue=libellerue,
        codepostal=codepostal,
        codecommune=codecommune,
    )


class RetrieveIncompleteAddressOperator(RetrieveAddressesOperator):

    def __init__(self, source_table: str = 'source', **kwargs: Any) -> None:
        self.get_records_mock = Mock(return_value=iter([TEST_VALUES]))
        self.mysql_hook_mock = MagicMock(MySqlHookOnDuplicateKey, get_records=self.get_records_mock)

        super().__init__(task_id='test', source_table=source_table, _mysql_hook=self.mysql_hook_mock, **kwargs)

        self.found_addresses: Optional[list[dict[str, str]]] = None
        self.inserted_addresses: Optional[list[dict[str, str]]] = None

    def _retrieve_addresses(self, incomplete_addresses: Iterator[dict[str, str]]) -> Addresses:
        self.found_addresses = list(incomplete_addresses)
        yield from []

    def _insert_addresses(self, address: Generator[dict[str, str], None, None]) -> None:
        self.inserted_addresses = list(address)


class RetrieveGeolocationOperator(RetrieveAddressesOperator):

    def __init__(self, source_table: str = 'source', **kwargs: Any) -> None:
        csv_content = self.create_csv_header() + "\n" + self.create_csv_row()
        self.http_hook_result = MagicMock(requests.Response, text=csv_content)
        self.http_hook_run_mock = Mock(return_value=self.http_hook_result)
        self.http_hook_mock = MagicMock(HttpHook, run=self.http_hook_run_mock)

        super().__init__(task_id='test', source_table=source_table, _http_hook=self.http_hook_mock, **kwargs)

        self.inserted_addresses: Optional[list[dict[str, str]]] = None
        self.retrieve_incomplete_address_mock_return_value: Iterable[dict[str, str]] = [_create_sql_result()]

    @property
    def csv_content(self) -> str:
        return str(self.http_hook_result.text)

    @csv_content.setter
    def csv_content(self, value: str) -> None:
        self.http_hook_result.text = value

    @csv_content.deleter
    def csv_content(self) -> None:
        del self.http_hook_result.text

    @staticmethod
    def create_csv_header() -> str:
        return "siret,full_address,city_code,latitude,longitude"

    @staticmethod
    def create_csv_row(siret: str = '12345678901234',
                       full_address: str = '1 RUE DU TEST 75001 PARIS',
                       city_code: str = '',
                       latitude: str = '47.840738',
                       longitude: str = '1.387486') -> str:
        return f'{siret},{full_address},{city_code},{latitude},{longitude}'

    def _retrieve_incomplete_address(self) -> Generator[dict[str, str], None, None]:
        yield from self.retrieve_incomplete_address_mock_return_value

    def _insert_addresses(self, address: Generator[dict[str, str], None, None]) -> None:
        self.inserted_addresses = list(address)


class InsertAddressesOperator(RetrieveAddressesOperator):

    def __init__(self, **kwargs: Any) -> None:
        self.mysql_hook_mock = MagicMock(MySqlHookOnDuplicateKey)
        super().__init__(task_id='test', source_table='test_table', _mysql_hook=self.mysql_hook_mock, **kwargs)

    def _retrieve_incomplete_address(self) -> Generator[dict[str, str], None, None]:
        yield _create_sql_result()

    def _retrieve_addresses(self, incomplete_addresses: Iterator[dict[str, str]]) -> Addresses:
        yield {'siret': 'siret value', 'coordinates_x': 'coordinates_x value', 'coordinates_y': 'coordinates_y value'}


class TestRetrieveAddresses(TestCase):

    def test_execute(self) -> None:
        operator = EmptyRetrieveAddressesOperator()

        operator.execute(Context())

        self.assertTrue(operator.retrieve_incomplete_address_called,
                        '_retrieve_incomplete_address should have been call')
        self.assertIsNotNone(operator.retrieved_addresses, '_retrieve_addresses should have been call')
        self.assertListEqual([{
            "ok": "_retrieve_incomplete_address"
        }], operator.retrieved_addresses, ('_retrieve_addresses should have been call with '
                                           '_retrieve_incomplete_address result'))
        self.assertIsNotNone(operator.inserted_addresses, '_insert_addresses should have been call')
        self.assertListEqual([{
            "ok": "_retrieve_addresses"
        }], operator.inserted_addresses, '_insert_addresses should have been call with _retrieve_addresses result')


class TestRetrieveIncompleteAddressOperator(TestCase):

    def setUp(self) -> None:
        self.operator = RetrieveIncompleteAddressOperator(source_table='test_table')
        self.operator.execute(Context())

    def test_retrieve_data_in_the_db(self) -> None:
        self.operator.get_records_mock.assert_called_once()

    def test_should_select_companies_in_the_db(self) -> None:
        sql: str = self.operator.get_records_mock.call_args[0][0]
        self.assertTrue(sql.startswith('SELECT '), 'the execute should select the rows')
        self.assertIn('FROM test_table', sql,
                      'the execute should select the rows in the "source_table" (from the kwarg)')

    def test_should_select_rows_required_to_retrieve_and_insert_addresses(self) -> None:

        def get_rows_from_sql_query(sql_query: str) -> list[str]:
            result = re.match('SELECT (.*) FROM', sql_query)
            assert result is not None, 'Request seem malformed, SELECT ... FROM not found in it'
            raw_rows = result.group(1)
            _rows = raw_rows.split(',')
            return list(map(str.strip, _rows))

        sql: str = self.operator.get_records_mock.call_args[0][0]
        rows = get_rows_from_sql_query(sql)
        self.assertEqual(REQUIRED_ROWS, rows, f"The database query should select : {REQUIRED_ROWS!r}.\nQuery:{sql}")

    def test_should_retrieve_addresses_with_query_result_as_dict(self) -> None:
        assert self.operator.found_addresses is not None, "_retrieve_addresses should have been call"
        self.assertListEqual(self.operator.found_addresses, [_create_sql_result()],
                             "The found addresses should be a dict")

    def test_should_retrieve_addresses_with_without_geoloc(self) -> None:
        sql: str = self.operator.get_records_mock.call_args[0][0]
        self.assertIn(' WHERE ', sql, "The database query should be filter")
        where_clause = sql.split(' WHERE ')[1]
        self.assertIn('coordinates_x IS NULL', where_clause, "The database query should be filter by the coordinates_x")
        self.assertIn('coordinates_y IS NULL', where_clause, "The database query should be filter by the coordinates_y")


class Unset:
    pass


class TestRetrieveGeolocationOperator(TestCase):

    def setUp(self) -> None:
        self.operator = RetrieveGeolocationOperator()

    def execute(self,
                nb_result: int = 1,
                **kwargs: str) -> tuple[list[str], list[list[str]], dict[str, Union[str, list[str]]]]:
        result = _create_sql_result(**kwargs)
        self.operator.retrieve_incomplete_address_mock_return_value = iter([result] * nb_result)
        self.operator.execute(Context())

        file_lines = self._retrieve_file_lines_in_http_kook_run_call_kwargs()
        params = self._retrieve_params()
        return file_lines[0], file_lines[1:], params

    def _retrieve_file_lines_in_http_kook_run_call_kwargs(self) -> list[list[str]]:
        self.assertTrue(self.operator.http_hook_mock.run.call_count, 'the operator should have call the api')
        call_kwargs = self.operator.http_hook_mock.run.call_args[1]
        files: dict[str, bytes] = call_kwargs["files"]
        self.assertIn('data', files, 'http_hook.run call should be call with a "data" file')
        file_content: bytes = files['data']
        self.assertIsInstance(file_content, bytes)
        str_file_content = file_content.decode()
        reader = csv.reader(str_file_content.splitlines())
        file_lines = list(reader)
        return file_lines

    def _retrieve_params(self) -> dict[str, Union[str, list[str]]]:
        call_kwargs = self.operator.http_hook_mock.run.call_args[1]
        params: dict[str, Union[str, list[str]]] = call_kwargs["params"]
        return params

    def test_should_call_the_api(self) -> None:
        self.operator.execute(Context())

        self.assertTrue(self.operator.http_hook_mock.run.call_count, 'the operator should call the api')
        self.operator.http_hook_mock.run.assert_called_once()
        uri = self.operator.http_hook_mock.run.call_args[0][0]
        self.assertEqual('/search/csv/', uri, 'the operator should call the /search/csv/ api')

    def test_should_call_the_api_with_a_file(self) -> None:
        message = 'the operator should call the api with a file'

        self.operator.execute(Context())

        self.operator.http_hook_mock.run.assert_called_once()
        call_kwargs = self.operator.http_hook_mock.run.call_args[1]
        self.assertIsNotNone(call_kwargs, message)
        self.assertIn("files", call_kwargs, message)
        self.assertIsNotNone(call_kwargs["files"], message)

    def test_run_files_should_contains_a_csv(self) -> None:
        message = 'the operator should call the api with a csv file'

        self.operator.execute(Context())

        files = self.operator.http_hook_mock.run.call_args[1]["files"]
        self.assertIn('data', files, message)
        file_content: bytes = files['data']
        self.assertIsInstance(file_content, bytes, message + " as bytes")
        str_file_content = file_content.decode()
        reader = csv.reader(str_file_content.splitlines())
        file_lines = list(reader)
        self.assertEqual(2, len(file_lines), message + " containing a header and one line per retrieved company")

    def test_run_files_should_have_the_required_rows(self) -> None:
        header, _, _ = self.execute()

        self.assertIn('siret', header, 'the csv file send to the API should contain the siret')
        self.assertIn('full_address', header, 'the csv file send to the API should contain the full_address')
        self.assertIn('citycode', header, 'the csv file send to the API should contain the city_code')

    def test_should_call_the_api_with_the_csv_columns(self) -> None:
        _, _, params = self.execute()

        self.assertIn('columns', params, 'the api should be call with a columns parameter')
        self.assertIn('city_code', params, 'the api should be call with a city_code parameter')
        self.assertEqual('full_address', params['columns'], 'the api should be call with "full_address" columns')
        self.assertEqual('city_code', params['city_code'],
                         'the api should be call with "city_code" in city_code parameter')

    def test_run_files_should_contains_the_csv(self) -> None:
        _, rows, _ = self.execute()

        self.assertEqual(1, len(rows),
                         'the api should be call with a csv file containing one line per retrieved company')
        self.assertIn("12345678901234", rows[0], 'the api should be call with a csv file containing the siret')
        self.assertIn("1 rue du test 75011 PARIS", rows[0], "the api csv should have the full address")
        self.assertIn("75056", rows[0], "the api csv should contain the citycode")

    def test_lieu_dit(self) -> None:
        _, rows, _ = self.execute(numerorue="KO", libellerue="LIEU DIT TEST")

        self.assertIn("TEST 75011 PARIS", rows[0], 'the csv full address should remove the LIEU DIT')

    def test_invalid_commune(self) -> None:
        result = _create_sql_result(codecommune="INVALID")
        self.operator.retrieve_incomplete_address_mock_return_value = iter([result])

        self.operator.execute(Context())

        self.assertEqual(0, self.operator.http_hook_mock.run.call_count,
                         "the invalid code commune shouldn't be send to the api")

    def test_call_the_api_by_bulk(self) -> None:
        _, rows, _ = self.execute(nb_result=2000)

        self.assertEqual(2, self.operator.http_hook_mock.run.call_count, 'the operator should have call twice the api')

    def test_retrieve_the_data_to_be_save(self) -> None:
        self.execute()

        assert self.operator.inserted_addresses is not None
        self.assertEqual(1, len(self.operator.inserted_addresses),
                         'the operator should be call with a list a one address to modify')
        self.assertIn("siret", self.operator.inserted_addresses[0],
                      'the address to modify should contain the siret of the company to modify')
        self.assertEqual("12345678901234", self.operator.inserted_addresses[0]["siret"],
                         "the siret to be inserted should be the one in the api result")
        self.assertIn("coordinates_x", self.operator.inserted_addresses[0],
                      'the address to modify should contain the coordinates (x)')
        self.assertIn("coordinates_y", self.operator.inserted_addresses[0],
                      'the address to modify should contain the coordinates (y)')
        self.assertEqual("1.387486", self.operator.inserted_addresses[0]["coordinates_x"],
                         "the x coordinate to be inserted should be the longitude from the api result")
        self.assertEqual("47.840738", self.operator.inserted_addresses[0]["coordinates_y"],
                         "the y coordinate to be inserted should be the latitude from the api result")

    def test_filter_retrieved_data_remove_lines_with_empty_result(self) -> None:
        self.operator.csv_content = "\n".join([
            self.operator.create_csv_header(),
            self.operator.create_csv_row(siret=''),
            self.operator.create_csv_row(longitude=''),
            self.operator.create_csv_row(latitude=''),
        ])

        self.execute()

        assert self.operator.inserted_addresses is not None
        self.assertIsNotNone(self.operator.inserted_addresses)
        self.assertEqual(0, len(self.operator.inserted_addresses),
                         'the operator should be call without the incomplete data (aka: none in this test)')


class TestInsertAddressesOperator(TestCase):

    def test_execute_should_upsert_rows(self) -> None:
        self.operator = InsertAddressesOperator()
        self.operator.execute(Context())

        self.operator.mysql_hook_mock.insert_rows.assert_called_once()
        call_args = self.operator.mysql_hook_mock.insert_rows.call_args

        with self.subTest("table"):
            self.assertEqual('test_table', call_args[0][0], 'Api Address Operator should insert in test_table')

        with self.subTest("rows"):
            rows = list(call_args[0][1])
            self.assertEqual(1, len(rows), 'Api Address Operator should insert the rows retrieved in the api')
            row = rows[0]

        with self.subTest("target_fields"):
            self.assertGreater(len(call_args[0]), 2, 'Api Address Operator should have a target_fields')
            target_fields = list(call_args[0][2])

        with self.subTest("rows siret"):
            siret_index = 0
            self.assertEqual("siret", target_fields[siret_index], 'The 1st field should be the siret')
            self.assertEqual("siret value", row[siret_index],
                             'Api Address Operator should insert the siret in the 1st row')

        with self.subTest("rows coordinates"):
            coordinates_x_index = 1
            coordinates_y_index = 2
            self.assertEqual("coordinates_x", target_fields[coordinates_x_index],
                             'The 1st field should be the coordinates_x')
            self.assertEqual("coordinates_x value", row[coordinates_x_index],
                             'Api Address Operator should insert the coordinates_x in the 2nd row')
            self.assertEqual("coordinates_y", target_fields[coordinates_y_index],
                             'The 1st field should be the coordinates_y')
            self.assertEqual("coordinates_y value", row[coordinates_y_index],
                             'Api Address Operator should insert the coordinates_y in the 3rd row')

        with self.subTest("on_duplicate_key_update"):
            kwargs = call_args[1]
            self.assertIn('on_duplicate_key_update', kwargs, 'Api Address should update on duplicate key')
            self.assertIn('coordinates_x', kwargs['on_duplicate_key_update'],
                          'Api Address should update coordinates_x on duplicate key')
            self.assertIn('coordinates_y', kwargs['on_duplicate_key_update'],
                          'Api Address should update coordinates_y on duplicate key')

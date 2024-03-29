import os.path
from os.path import dirname, join
from typing import Dict, Optional, Any
from unittest import TestCase, skipUnless
from unittest.mock import Mock, MagicMock, patch, call, mock_open

import _csv
from airflow.hooks.filesystem import FSHook
from airflow.providers.mysql.hooks.mysql import MySqlHook

from common.custom_types import Context
from operators.extract_offices import ExtractOfficesOperator, Office, FIELDS

TEST_DIR = join(dirname(dirname(dirname(__file__))), 'tests')

VALID_HEADER = 'siret;raisonsociale;enseigne;codenaf;numerorue;libellerue;codecommune;codepostal;email;tel;' \
               'trancheeffectif;website;flag_poe_afpr;flag_pmsmp;flag_junior;flag_senior;flag_handicap'


def create_office(siret: str = '00000000001941', **overloaded_kwargs: Any) -> Office:
    kwargs: Dict[str, Any]

    kwargs = dict(raisonsociale='ASS MUSARAILE',
                  enseigne='',
                  codenaf='9312Z',
                  numerorue='5',
                  libellerue='SQUARE GEORGES GUYON',
                  codecommune='94046',
                  codepostal='94700',
                  email='',
                  tel='0143565222',
                  trancheeffectif='NULL',
                  website='',
                  flag_poe_afpr='0',
                  flag_pmsmp='0',
                  flag_junior='NULL',
                  flag_senior='NULL',
                  flag_handicap='NULL')
    kwargs.update(**overloaded_kwargs)

    return Office(siret=siret, **kwargs)


def create_office_with_default() -> Office:
    return create_office(trancheeffectif=None, flag_junior=False, flag_senior=False, flag_handicap=False)


class OfficeTestCase(TestCase):

    @patch('operators.extract_offices.get_department_from_zipcode', return_value="OK")
    def test_department(self, _: Mock) -> None:
        office = create_office()
        self.assertEqual(office.departement, "OK")


class TestExtractOfficesOperator(TestCase):
    office_filename = join(TEST_DIR, 'data', 'lbb-output-wf-202202150303-extracted', 'etablissements',
                           'etablissements.csv')

    def execute(self,
                _mysql_hook: Optional[MySqlHook] = None,
                offices_filename: Optional[str] = None,
                max_lines_to_treat: Optional[int] = None) -> int:
        mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
        mock_mysql_hook = _mysql_hook or MagicMock(MySqlHook)
        offices_filename = offices_filename or self.office_filename
        operator = ExtractOfficesOperator(offices_filename=offices_filename,
                                          destination_table='test_table',
                                          task_id="test_task",
                                          chunk_size=5,
                                          max_lines_to_treat=max_lines_to_treat,
                                          _fs_hook=mock_fs_hook,
                                          _mysql_hook=mock_mysql_hook)
        return operator.execute(Context())

    def execute_with_file_content(self,
                                  _mysql_hook: Optional[MySqlHook] = None,
                                  header: str = VALID_HEADER,
                                  **overloaded_values: str) -> int:
        file_content = create_office(**overloaded_values)
        csv_fields = map(str, [
            file_content.siret, file_content.raisonsociale, file_content.enseigne, file_content.codenaf,
            file_content.numerorue, file_content.libellerue, file_content.codecommune, file_content.codepostal,
            file_content.email, file_content.tel, file_content.trancheeffectif, file_content.website,
            file_content.flag_poe_afpr, file_content.flag_pmsmp, file_content.flag_junior, file_content.flag_senior,
            file_content.flag_handicap
        ])

        def add_quote(field: str) -> str:
            if ';' in field:
                return f'"{field}"'
            return field

        csv_fields_with_quote = map(add_quote, csv_fields)
        mocked_open = mock_open(read_data=f"{header}\n{';'.join(csv_fields_with_quote)}\n")
        with patch('operators.extract_offices.open', mocked_open):
            return self.execute(offices_filename='memory', _mysql_hook=_mysql_hook)

    def test_fields(self) -> None:
        success, error = ExtractOfficesOperator.check_fields()
        self.assertTrue(success, f'all fields should be referenced in the Office object. Missing fields: {list(error)}')

    def test_coherence_between_FIELDS_and_Office_props(self) -> None:
        missing_fields = set(FIELDS) - set(vars(Office))
        if missing_fields:
            message = f"All fields in ExtractOfficesOperator should be in the Office props. Missing : {missing_fields}"
            self.fail(message)

    def test_get_offices_from_file(self) -> None:
        mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
        operator = ExtractOfficesOperator(offices_filename=self.office_filename,
                                          destination_table='test_table',
                                          task_id="test_task",
                                          chunk_size=1000,
                                          _fs_hook=mock_fs_hook)
        expected_result = create_office_with_default()

        result = next(operator._get_offices_from_file())

        self.assertIsInstance(result, dict)
        self.assertEqual(9, len(result))
        self.assertIn("00000000001941", result)
        self.maxDiff = None
        self.assertEqual(result["00000000001941"], expected_result)

    def test_get_offices_from_file_with_chunk(self) -> None:
        mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
        operator = ExtractOfficesOperator(offices_filename=self.office_filename,
                                          destination_table='test_table',
                                          task_id="test_task",
                                          chunk_size=5,
                                          _fs_hook=mock_fs_hook)
        result = list(operator._get_offices_from_file())
        self.assertEqual(2, len(result))
        self.assertEqual(5, len(result[0]))
        self.assertEqual(4, len(result[1]))

    def test_execute_create_companies(self) -> None:
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.insert_rows = Mock()
        with patch('operators.extract_offices.FIELDS', ['siret']):
            self.execute(_mysql_hook=mock_mysql_hook)

        self.assertEqual(2, mock_mysql_hook.insert_rows.call_count)
        mock_mysql_hook.insert_rows.assert_called_with(
            'test_table',
            [["00000488794926"], ["00000533026381"], ["00000599101508"], ["00000815184353"]],
            ['siret'],
            on_duplicate_key_update=True,
        )

    def test_NULL_values_are_saved_with_null(self) -> None:
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.insert_rows = Mock()
        nb_inserted_siret = self.execute_with_file_content(trancheeffectif='NULL', _mysql_hook=mock_mysql_hook)

        self.assertEqual(1, nb_inserted_siret)
        result = mock_mysql_hook.insert_rows.call_args[0][1][0][FIELDS.index('trancheeffectif')]
        self.assertEqual(None, result, 'The NULL values should be insert in the DB as None')

    def test_trancheffectif_should_be_transformed(self) -> None:
        mock_mysql_hook = MagicMock(MySqlHook)

        nb_inserted_siret = self.execute_with_file_content(trancheeffectif='0-0', _mysql_hook=mock_mysql_hook)

        self.assertEqual(1, nb_inserted_siret)
        result = mock_mysql_hook.insert_rows.call_args[0][1][0][FIELDS.index('trancheeffectif')]
        self.assertEqual("00", result, 'The "trancheeffectif" should be transform from "0-0" to "00"')

    @patch('operators.extract_offices.is_siret', return_value=False)
    def test_siret_format(self, is_siret_mock: Mock) -> None:
        nb_invalid_inserted_siret = self.execute_with_file_content(siret='invalid siret')

        is_siret_mock.assert_called_with('invalid siret')  # Siret should be check using common.is_siret method
        self.assertEqual(0, nb_invalid_inserted_siret, "Office with invalid siret shouldn't be save")

        nb_null_inserted_siret = self.execute_with_file_content(siret='NULL')

        self.assertEqual(0, nb_null_inserted_siret, "Office with NULL shouldn't be save")

    @patch('operators.extract_offices.get_department_from_zipcode', return_value='99')
    @patch('operators.extract_offices.DEPARTEMENTS', new=['01'])
    def test_department(self, get_department_from_zipcode_mock: Mock) -> None:
        nb_inserted_siret = self.execute_with_file_content(codepostal='99999')

        get_department_from_zipcode_mock.assert_called_with('99999')
        self.assertEqual(0, nb_inserted_siret,
                         "Office with a department not referenced in the DEPARTEMENTS shouldn't be save")

    def test_row_with_invalid_trancheffectif(self) -> None:
        nb_inserted_siret = self.execute_with_file_content(trancheeffectif='0-2')

        self.assertEqual(0, nb_inserted_siret, 'rows with invalid "trancheeffectif" should be skip')

    def test_row_with_NULL_trancheffectif(self) -> None:
        mock_mysql_hook = MagicMock(MySqlHook)

        nb_inserted_siret = self.execute_with_file_content(trancheeffectif='NULL', _mysql_hook=mock_mysql_hook)

        self.assertEqual(1, nb_inserted_siret, 'rows with NULL "trancheeffectif" should be add')
        result = mock_mysql_hook.insert_rows.call_args[0][1][0][FIELDS.index('trancheeffectif')]
        self.assertIsNone(result, 'The "trancheeffectif" should be add as "None"')

    def test_row_with_null_raisonsociale_should_be_skip(self) -> None:
        nb_inserted_siret = self.execute_with_file_content(raisonsociale='NULL')

        self.assertEqual(0, nb_inserted_siret, 'rows with NULL in the "raisonsocial" shouldn\'t be treated')

    def test_NULL_values_are_saved_with_default(self) -> None:
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.insert_rows = Mock()
        with patch('operators.extract_offices.FIELDS', ['flag_junior']):
            self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.insert_rows.assert_called_with(
            'test_table',
            [[False], [False], [False], [False]],
            ['flag_junior'],
            on_duplicate_key_update=True,
        )

    def test_execute_delete_expired_sirets(self) -> None:
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.get_records = Mock(return_value=[("51837000000001",), ("51837000000002",)])

        self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.get_records.assert_called_once_with('SELECT siret FROM test_table')
        mock_mysql_hook.run.assert_called_once()
        expected_query_1 = 'DELETE FROM `test_table` WHERE `siret` IN ("51837000000001", "51837000000002")'
        expected_query_2 = 'DELETE FROM `test_table` WHERE `siret` IN ("51837000000002", "51837000000001")'
        if (mock_mysql_hook.run.call_args != call([expected_query_1])
                and mock_mysql_hook.run.call_args != call([expected_query_2])):
            self.fail(f"Extra companies should be delete, got :\n{mock_mysql_hook.run.call_args}")

    def test_execute_don_t_delete_not_expired_sirets(self) -> None:
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.get_records = Mock(return_value=[("00000000001941",)])
        mock_mysql_hook.run = Mock()
        self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.run.assert_not_called()

    def test_execute_don_t_delete_invalid_sirets(self) -> None:
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.get_records = Mock(return_value=[("invalids",)])
        mock_mysql_hook.run = Mock()
        self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.run.assert_not_called()

    def test_file_with_extra_column_should_skip_it(self) -> None:
        raisonsociale_with_semicolon = "SQUARE GEORGES; GUYON"
        insert_rows_mock = MagicMock(MySqlHook)
        mock_mysql_hook = MagicMock(MySqlHook, insert_rows=insert_rows_mock)

        nb_inserted_sirets = self.execute_with_file_content(_mysql_hook=mock_mysql_hook,
                                                            raisonsociale=raisonsociale_with_semicolon)

        self.assertEqual(1, nb_inserted_sirets)
        insert_rows__args = insert_rows_mock.call_args[0]
        insert_rows__rows = insert_rows__args[1]
        self.assertIn('SQUARE GEORGES; GUYON', insert_rows__rows[0], 'the raison social should have the semi colon')

    def test_quotes_should_be_treated(self) -> None:
        insert_rows_mock = Mock()
        mock_mysql_hook = MagicMock(MySqlHook, insert_rows=insert_rows_mock)

        nb_inserted_sirets = self.execute_with_file_content(raisonsociale='"quoted name', _mysql_hook=mock_mysql_hook)

        self.assertEqual(0, nb_inserted_sirets)

    def test_execute_should_limit_rows(self) -> None:
        nb_inserted_sirets = self.execute(max_lines_to_treat=1)

        self.assertEqual(1, nb_inserted_sirets)

    @skipUnless(os.path.exists(join(TEST_DIR, 'data', 'huge_test.csv')), 'huge_test doesn\'t exists')
    def test_file_with_huge_file(self) -> None:
        try:
            self.execute(offices_filename=join(TEST_DIR, 'data', 'huge_test.csv'))
        except _csv.Error:
            self.fail("Huge file should succeed")

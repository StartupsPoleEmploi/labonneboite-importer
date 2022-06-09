import os.path
from os.path import dirname, join
from typing import Optional
from unittest import TestCase, skipUnless
from unittest.mock import Mock, MagicMock, patch, call, mock_open

import _csv
from airflow.hooks.filesystem import FSHook
from airflow.providers.mysql.hooks.mysql import MySqlHook

from operators.extract_offices import ExtractOfficesOperator, Office, FIELDS

TEST_DIR = join(dirname(dirname(dirname(__file__))), 'tests')

VALID_HEADER = 'siret;raisonsociale;enseigne;codenaf;numerorue;libellerue;codecommune;codepostal;email;tel;' \
               'trancheeffectif;website;flag_poe_afpr;flag_pmsmp;flag_junior;flag_senior;flag_handicap'


def create_office(**overloaded_kwargs):
    kwargs = dict(siret='00000000001941', raisonsociale='ASS MUSARAILE', enseigne='', codenaf='9312Z',
                  numerorue='5', libellerue='SQUARE GEORGES GUYON', codecommune='94046',
                  codepostal='94700', email='', tel='0143565222', trancheeffectif='NULL', website='',
                  flag_poe_afpr='0', flag_pmsmp='0', flag_junior='NULL', flag_senior='NULL',
                  flag_handicap='NULL')
    kwargs.update(**overloaded_kwargs)
    return Office(**kwargs)


def create_office_with_default():
    return create_office(
        trancheeffectif=None,
        flag_junior=False,
        flag_senior=False,
        flag_handicap=False
    )


class OfficeTestCase(TestCase):

    @patch('operators.extract_offices.get_department_from_zipcode', return_value="OK")
    def test_department(self, _: Mock):
        office = create_office()
        self.assertEqual(office.departement, "OK")


class TestExtractOfficesOperator(TestCase):
    office_filename = join(TEST_DIR, 'data', 'lbb-output-wf-202202150303-extracted',
                           'etablissements', 'etablissements.csv')

    def execute(self, _mysql_hook: Optional[MySqlHook] = None, offices_filename: Optional[str] = None):
        mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
        mock_mysql_hook = _mysql_hook or MagicMock(MySqlHook)
        offices_filename = offices_filename or self.office_filename
        operator = ExtractOfficesOperator(offices_filename=offices_filename,
                                          destination_table='test_table',
                                          task_id="test_task",
                                          chunk_size=5,
                                          _fs_hook=mock_fs_hook,
                                          _mysql_hook=mock_mysql_hook)
        return operator.execute({})

    def execute_with_file_content(self, _mysql_hook: Optional[MySqlHook] = None, header=VALID_HEADER,
                                  **overloaded_values: str):
        file_content = create_office(**overloaded_values)
        csv_fields = [file_content.siret, file_content.raisonsociale, file_content.enseigne, file_content.codenaf,
                      file_content.numerorue, file_content.libellerue, file_content.codecommune,
                      file_content.codepostal, file_content.email, file_content.tel, file_content.trancheeffectif,
                      file_content.website, file_content.flag_poe_afpr, file_content.flag_pmsmp,
                      file_content.flag_junior, file_content.flag_senior, file_content.flag_handicap]
        mocked_open = mock_open(read_data=f"{header}\n{';'.join(csv_fields)}\n")
        with patch('operators.extract_offices.open', mocked_open):
            return self.execute(offices_filename='memory', _mysql_hook=_mysql_hook)

    def test_coherence_between_FIELDS_and_Office_props(self):
        missing_fields = set(FIELDS) - set(vars(Office))
        if missing_fields:
            message = f"All fields in ExtractOfficesOperator should be in the Office props. Missing : {missing_fields}"
            self.fail(message)

    def test_get_offices_from_file(self):
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

    def test_get_offices_from_file_with_chunk(self):
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

    def test_execute_create_companies(self):
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.insert_rows = Mock()
        with patch('operators.extract_offices.FIELDS', ['siret']):
            self.execute(_mysql_hook=mock_mysql_hook)

        self.assertEqual(2, mock_mysql_hook.insert_rows.call_count)
        mock_mysql_hook.insert_rows.assert_called_with(
            'test_table',
            [["00000488794926"], ["00000533026381"], ["00000599101508"], ["00000815184353"]],
            ['siret'],
            replace=True,
        )

    def test_NULL_values_are_saved_with_null(self):
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.insert_rows = Mock()
        with patch('operators.extract_offices.FIELDS', ['trancheeffectif']):
            self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.insert_rows.assert_called_with(
            'test_table',
            [[None], [None], [None], [None]],
            ['trancheeffectif'],
            replace=True,
        )

    def test_trancheffectif_should_be_transformed(self):
        mock_mysql_hook = MagicMock(MySqlHook)

        nb_inserted_siret = self.execute_with_file_content(trancheeffectif='0-0', _mysql_hook=mock_mysql_hook)

        self.assertEqual(1, nb_inserted_siret)
        result = mock_mysql_hook.insert_rows.call_args[0][1][0][FIELDS.index('trancheeffectif')]
        self.assertEqual("00", result)

    def test_NULL_values_are_saved_with_default(self):
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.insert_rows = Mock()
        with patch('operators.extract_offices.FIELDS', ['flag_junior']):
            self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.insert_rows.assert_called_with(
            'test_table',
            [[False], [False], [False], [False]],
            ['flag_junior'],
            replace=True,
        )

    def test_execute_delete_expired_sirets(self):
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.get_records = Mock(return_value=[("51837000000001",), ("51837000000002",)])

        self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.get_records.assert_called_once_with(
            'SELECT siret FROM test_table'
        )
        mock_mysql_hook.run.assert_called_once()
        expected_query_1 = 'DELETE FROM "test_table" WHERE "siret" IN ("51837000000001", "51837000000002")'
        expected_query_2 = 'DELETE FROM "test_table" WHERE "siret" IN ("51837000000002", "51837000000001")'
        if (mock_mysql_hook.run.call_args != call([expected_query_1]) and mock_mysql_hook.run.call_args != call(
                [expected_query_2])):
            self.fail(f"Extra companies should be delete, got :\n{mock_mysql_hook.run.call_args}")

    def test_execute_don_t_delete_not_expired_sirets(self):
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.get_records = Mock(return_value=[("00000000001941",)])
        mock_mysql_hook.run = Mock()
        self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.run.assert_not_called()

    def test_execute_don_t_delete_invalid_sirets(self):
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.get_records = Mock(return_value=[("invalids",)])
        mock_mysql_hook.run = Mock()
        self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.run.assert_not_called()

    def test_file_with_extra_column_should_skip_it(self):
        raisonsociale_with_semicolon = "SQUARE GEORGES; GUYON"
        insert_rows_mock = MagicMock(MySqlHook)

        nb_inserted_sirets = self.execute_with_file_content(_mysql_hook=insert_rows_mock,
                                                            raisonsociale=raisonsociale_with_semicolon)

        self.assertEqual(0, nb_inserted_sirets)

    def test_quotes_should_be_treated(self):
        insert_rows_mock = Mock()
        mock_mysql_hook = MagicMock(MySqlHook, insert_rows=insert_rows_mock)

        nb_inserted_sirets = self.execute_with_file_content(raisonsociale='"quoted name', _mysql_hook=mock_mysql_hook)

        self.assertEqual(1, nb_inserted_sirets)
        insert_rows__args = insert_rows_mock.call_args[0]
        insert_rows__rows = insert_rows__args[1]
        self.assertIn('"quoted name', insert_rows__rows[0], 'the raison social should have the quote')

    @skipUnless(os.path.exists(join(TEST_DIR, 'data', 'huge_test.csv')), 'huge_test doesn\'t exists')
    def test_file_with_huge_file(self):
        try:
            self.execute(offices_filename=join(TEST_DIR, 'data', 'huge_test.csv'))
        except _csv.Error:
            self.fail("Huge file should succeed")

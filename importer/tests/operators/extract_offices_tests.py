from os.path import dirname, join
from typing import Optional
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch, call

from airflow.hooks.filesystem import FSHook
from airflow.providers.mysql.hooks.mysql import MySqlHook

from operators.extract_offices import ExtractOfficesOperator, Office, FIELDS

TEST_DIR = join(dirname(dirname(dirname(__file__))), 'tests')


def create_office(**overloaded_kwargs):
    kwargs = dict(siret='00000000001941', raisonsociale='ASS MUSARAILE', enseigne='', codenaf='9312Z',
                  numerorue='5', libellerue='SQUARE GEORGES GUYON', codecommune='94046',
                  codepostal='94700', email='', tel='0143565222', trancheeffectif='NULL', website='',
                  flag_poe_afpr='0', flag_pmsmp='0', flag_junior='NULL', flag_senior='NULL',
                  flag_handicap='NULL')
    kwargs.update(**overloaded_kwargs)
    return Office(**kwargs)


class OfficeTestCase(TestCase):

    @patch('operators.extract_offices.get_department_from_zipcode', return_value="OK")
    def test_department(self, _: Mock):
        office = create_office()
        self.assertEqual(office.departement, "OK")


class TestExtractOfficesOperator(TestCase):
    office_filename = join(TEST_DIR, 'data', 'lbb-output-wf-202202150303-extracted',
                           'etablissements', 'etablissements.csv')

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
        result = next(operator._get_offices_from_file())
        self.assertIsInstance(result, dict)
        self.assertEqual(9, len(result))
        self.assertIn("00000000001941", result)
        self.maxDiff = None
        self.assertEqual(result["00000000001941"], create_office())

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

    def execute(self, _mysql_hook: Optional[MySqlHook] = None):
        mock_fs_hook = MagicMock(FSHook, get_path=Mock(return_value="/"))
        mock_mysql_hook = _mysql_hook or MagicMock(MySqlHook)
        operator = ExtractOfficesOperator(offices_filename=self.office_filename,
                                          destination_table='test_table',
                                          task_id="test_task",
                                          chunk_size=5,
                                          _fs_hook=mock_fs_hook,
                                          _mysql_hook=mock_mysql_hook)
        operator.execute({})

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

    def test_execute_delete_expired_sirets(self):
        mock_mysql_hook = MagicMock(MySqlHook)
        mock_mysql_hook.get_records = Mock(return_value=[("51837000000001",), ("51837000000002",)])

        self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.get_records.assert_called_once_with(
            'SELECT "siret" FROM "test_table"'
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
        mock_mysql_hook.get_records = Mock(return_value=[("invalid",)])
        mock_mysql_hook.run = Mock()
        self.execute(_mysql_hook=mock_mysql_hook)

        mock_mysql_hook.run.assert_not_called()

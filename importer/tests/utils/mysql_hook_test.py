from typing import Optional, Dict, Tuple
from unittest import TestCase
from unittest.mock import MagicMock, Mock

from mysql.connector.abstracts import MySQLConnectionAbstract

from utils.mysql_hook import MySqlHookOnDuplicateKey


class MySqlHookOnDuplicateKeyWithoutConnexions(MySqlHookOnDuplicateKey):
    """MySqlHookOnDuplicateKey without the insert_rows method"""

    def __init__(self):
        super().__init__()
        self.last_result: Optional[str] = None

    def insert_rows(self, table, rows, target_fields=None, commit_every=1000, replace=False, **kwargs):
        for row in rows:
            sql = self._generate_insert_sql(table, tuple(row), target_fields, replace, **kwargs)
            self.last_result = sql


class MySqlHookOnDuplicateKeyInsertRows(MySqlHookOnDuplicateKey):
    """MySqlHookOnDuplicateKey without the connections methods"""

    def __init__(self):
        super().__init__()
        self.supports_autocommit = False
        self.test_conn = MagicMock(MySQLConnectionAbstract)
        self.test_cursor = MagicMock()
        self.test_conn.cursor = Mock(return_value=self.test_cursor)
        self.test_connection_opened = False
        self._generate_insert_sql = Mock(return_value='SQL QUERY')

    def get_conn(self):
        self.test_connection_opened = True
        return self.test_conn


class MySqlHookOnDuplicateKeyTestInsertRows(TestCase):
    """
    Test MySqlHookOnDuplicateKey.insert_rows
    """
    expected_result = "INSERT INTO table_name (siret, score) VALUES (%(siret)s,%(score)s)"

    def test_expect_connection_to_be_open(self):
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', [])

        self.assertTrue(hook.test_connection_opened)
        hook.test_conn.cursor.assert_called_once_with()

    @staticmethod
    def test_expect_connection_to_close():
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', [])
        hook.test_cursor.close.assert_called_once_with()
        hook.test_conn.close.assert_called_once_with()

    @staticmethod
    def test_expect_sql_to_be_generated():
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', [['val1', 'val2']])
        hook._generate_insert_sql.assert_called_once()

    def test_expect_cursor_to_execute_generated_sql(self):
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', [['val1', 'val2']])
        hook.test_cursor.execute.assert_called_once()
        self.assertEqual('SQL QUERY', hook.test_cursor.execute.call_args[0][0])

    def test_expect_cursor_to_execute_with_values(self):
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', [['val1', 'val2']])
        hook.test_cursor.execute.assert_called_once()
        self.assertEqual(('val1', 'val2'), hook.test_cursor.execute.call_args[0][1])

    def test_expect_cursor_to_execute_with_all_values(self):
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', [['val1', 'val2'], ['val3', 'val4']])
        self.assertEqual(2, hook.test_cursor.execute.call_count)
        self.assertEqual(('val3', 'val4'), hook.test_cursor.execute.call_args[0][1])

    def test_with_target_fields_expect_execute_values_to_be_a_dict(self):
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', [['012345678', '1']], ['col1', 'col2'])
        call_args = hook.test_cursor.execute.call_args[0]
        result_values = call_args[1]
        self.assertIsInstance(result_values, Dict)

    def test_without_target_fields_expect_execute_values_to_be_a_tuple(self):
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', [['012345678', '1']])
        call_args = hook.test_cursor.execute.call_args[0]
        result_values = call_args[1]
        self.assertIsInstance(result_values, Tuple)

    def test_expect_commit_to_be_call_if_commit_every_pass(self):
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', [['val']] * 70, commit_every=50)
        self.assertEqual(3, hook.test_conn.commit.call_count)

    def test_expect_work_with_iterators(self):
        hook = MySqlHookOnDuplicateKeyInsertRows()
        hook.insert_rows('table_name', iter([['val']] * 70))
        self.assertEqual(70, hook.test_cursor.execute.call_count)

    def test_with_default_expect_to_insert_into_the_table_name(self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [[]])
        self.assertIn("INSERT INTO table_name", hook.last_result)

    def test_with_replace_expect_to_replace_into_the_table_name(self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [[]], replace=True)
        self.assertIn("REPLACE INTO table_name", hook.last_result)

    def test_without_target_fields_expect_result_to_not_containing_columns(self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [[]])
        self.assertIn("table_name  VALUES", hook.last_result)

    def test_with_target_fields_expect_result_to_containing_columns(self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [[]], ['col1', 'col2'])
        self.assertIn("table_name (col1, col2) VALUES", hook.last_result)

    def test_without_target_fields_expect_result_to_use_basic_format_base_on_the_number_of_values(self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [['012345678', '1']])
        self.assertIn("(%s,%s)", hook.last_result)

    def test_with_target_fields_expect_result_to_use_named_format(self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [['012345678', '1']], ['col1', 'col2'])
        self.assertIn("(%(col1)s,%(col2)s)", hook.last_result)


    def test_without_on_duplicate_key_update_arg_expect_result_to_not_have_ON_DUPLICATE_KEY_UPDATE(self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [['012345678', '1']], ['siret', 'score'], on_duplicate_key_update=False)
        self.assertNotIn(" ON DUPLICATE KEY UPDATE ", hook.last_result)

    def test_on_duplicate_key_update_arg_should_have_ON_DUPLICATE_KEY_UPDATE(self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [['012345678', '1']], ['siret', 'score'], on_duplicate_key_update=True)
        self.assertIn(" ON DUPLICATE KEY UPDATE ", hook.last_result)

    def test_on_duplicate_key_update_arg_with_a_column_should_return_this_column_only_in_ON_DUPLICATE_KEY_UPDATE_clause(
            self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [['012345678', '1']], ['siret', 'score'], on_duplicate_key_update=['score'])
        self.assertIn(" ON DUPLICATE KEY UPDATE ", hook.last_result)
        _, on_duplicate_key_update_clause = hook.last_result.split(" ON DUPLICATE KEY UPDATE ")
        self.assertEqual("score=%(score)s", on_duplicate_key_update_clause)

    def test_on_duplicate_key_update_arg_set_to_true_should_return_all_column_in_ON_DUPLICATE_KEY_UPDATE_clause(self):
        hook = MySqlHookOnDuplicateKeyWithoutConnexions()
        hook.insert_rows('table_name', [['012345678', '1']], ['siret', 'score'], on_duplicate_key_update=True)
        _, on_duplicate_key_update_clause = hook.last_result.split(" ON DUPLICATE KEY UPDATE ")
        self.assertEqual("siret=%(siret)s, score=%(score)s", on_duplicate_key_update_clause)

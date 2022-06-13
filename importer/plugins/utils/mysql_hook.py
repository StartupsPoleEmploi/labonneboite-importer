from contextlib import closing
from typing import Union, List, Tuple, Iterable, Any, Dict

from airflow.providers.mysql.hooks.mysql import MySqlHook


class MySqlHookOnDuplicateKey(MySqlHook):
    def insert_rows(self, table, rows, target_fields=None, commit_every=1000, replace=False,
                    on_duplicate_key_update: Union[bool, Iterable[str]] = False, **kwargs):
        i = 0
        with closing(self.get_conn()) as conn:
            if self.supports_autocommit:
                self.set_autocommit(conn, False)

            conn.commit()

            with closing(conn.cursor()) as cur:
                for i, row in enumerate(rows, 1):
                    values = self._generate_values(conn, row, target_fields)
                    sql = self._generate_insert_sql(table, values, target_fields, replace,
                                                    on_duplicate_key_update=on_duplicate_key_update, **kwargs)
                    self.log.debug("Generated sql: %s", sql)
                    cur.execute(sql, values)
                    if commit_every and i % commit_every == 0:
                        conn.commit()
                        self.log.info("Loaded %s rows into %s so far", i, table)

            conn.commit()
        self.log.info("Done loading. Loaded a total of %s rows", i)

    @classmethod
    def _generate_insert_sql(
            cls,
            table: str,
            values: Tuple,
            target_fields: Iterable[str],
            replace: bool,
            on_duplicate_key_update: Union[bool, Iterable[str]] = False,
            **kwargs) -> str:

        if target_fields:
            placeholders = [
                f"%({key})s"
                for key in target_fields
            ]
            columns = ", ".join(target_fields)
            columns = f"({columns})"
        else:
            placeholders = ["%s"] * len(values)
            columns = ''

        if not replace:
            sql = "INSERT INTO "
        else:
            sql = "REPLACE INTO "
        sql += f"{table} {columns} VALUES ({','.join(placeholders)})"
        sql += cls._generate_insert_on_duplicate_key_update(target_fields, on_duplicate_key_update)
        return sql

    @staticmethod
    def _generate_insert_on_duplicate_key_update(target_fields: Iterable[str],
                                                 on_duplicate_key_update: Union[bool, Iterable[str]]):
        sql = ""
        if on_duplicate_key_update:
            if isinstance(on_duplicate_key_update, bool):
                on_duplicate_key_update = target_fields
            placeholders: List[str] = []
            for key in on_duplicate_key_update:
                if key in target_fields:
                    placeholder = f"{key}=%({key})s"
                    placeholders.append(placeholder)
            sql += f" ON DUPLICATE KEY UPDATE {', '.join(placeholders)}"
        return sql

    def _generate_values(
            self, conn, row: Iterable[Any], target_fields: Iterable[str]
    ) -> Union[Tuple[Any], Dict[str, Any]]:
        lst = []
        for cell in row:
            lst.append(self._serialize_cell(cell, conn))
        if target_fields:
            values = {target_field: value for target_field, value in zip(target_fields, lst)}
        else:
            values = tuple(lst)
        return values

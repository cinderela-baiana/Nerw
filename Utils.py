"""Algumas utilidades."""

from collections import namedtuple
import sqlite3

Field = namedtuple("Field", ("name", "type"))

class DatabaseWrap:
    """Provê funções que 'enrolam' chamadas cruas ao banco de dados."""

    def __init__(self, database):
        self.cursor = database.cursor()
        self.database = database

    @classmethod
    def from_filepath(cls, filename):
        return cls(sqlite3.connect(filename))

    def create_table_if_absent(self, table_name,  fields):
        """Cria uma tabela do SQLite se inexistente"""
        cl = []

        for field in fields:
            print(field)
            cl.append(f"{field.name}\t{field.type}")
        joined = ",\n".join(cl)
        sql = f"""
        CREATE TABLE IF NOT EXISTS "{table_name}"(
            {joined}
        );
        """

        self.cursor.execute(sql)
        self.database.commit()

    def get_item(self, table_name: str, where: str, item_name: str=None):
        if item_name is None:
            item_name = "*"

        sql = f"""SELECT {item_name} FROM {table_name} WHERE {where}"""
        self.cursor.execute(sql)
        fetched = self.cursor.fetchall()

        return fetched




"""Algumas utilidades."""

from collections import namedtuple
from discord.ext import commands

import sqlite3

Field = namedtuple("Field", ("name", "type"))

class DatabaseWrap:
    def __init__(self, database):
        self.cursor = database.cursor()
        self.database = database
        self.closed = False

    @classmethod
    def from_filepath(cls, filename):
        return cls(sqlite3.connect(filename))

    def create_table_if_absent(self, table_name,  fields):
        """Cria uma tabela do SQLite se inexistente"""
        cl = []

        for field in fields:
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
        fetched = self.cursor.fetchone()

        return fetched

    def remove_item(self, table_name: str, condition: str):
        sql = f"DELETE FROM {table_name} WHERE {condition}"

        self.cursor.execute(sql)
        self.database.commit()
        self.close()

    def close(self):
        """
        Fecha a conexão com o banco de dados.
        Essa função não tem efeito se já fechado.
        """
        if not self.closed:
            self.closed = True
            self.database.close()

    def reopen(self):
        """
        Reabre a conexão com o banco de dados
        Não tem efeito se não estiver fechado.

        Nota: Essa função retorna uma instância diferente da
                usada para chamar-lá.
        """
        if self.closed:
            ins = DatabaseWrap.from_filepath("main.db")
            return ins

def is_blacklisted():
    connection = DatabaseWrap.from_filepath("main.db")

    async def actual(ctx):
        item = connection.get_item("blacklisteds", f"user_id = {ctx.author.id}", 'user_id')

        return item is None

    return commands.check(actual)


"""Algumas utilidades."""

from collections import namedtuple
from discord.ext import commands
from typing import *

import sqlite3
import aiosqlite
import contextlib
import pathlib

PathLike = Union[str, pathlib.Path]

@contextlib.asynccontextmanager
async def create_async_database(path: PathLike):
    connection = await AsyncDatabaseWrap.from_filepath(path)
    try:
        yield connection
    finally:
        await connection.close()

Field = namedtuple("Field", ("name", "type"))

class DatabaseWrap:
    def __init__(self, database: sqlite3.Connection):
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

    def get_item(self, table_name: str, where: str=None, item_name: str=None, *, fetchall=False):
        if item_name is None:
            item_name = "*"

        sql = f"SELECT {item_name} FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        self.cursor.execute(sql)

        if fetchall:
            fetched = self.cursor.fetchall()
        else:
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise exc_val
        self.database.commit()
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

class AsyncDatabaseWrap(DatabaseWrap):
    def __init__(self, connection: aiosqlite.Connection):
        self._connection = connection
        self.closed = False
        self._cursor: Optional[aiosqlite.Cursor] = None

    async def create_table_if_absent(self, table_name: str, fields: List[Field]) -> None:
        await self._create_cursor()
        cl = []

        for field in fields:
            cl.append(f"{field.name}\t{field.type}")
        joined = ",\n".join(cl)
        sql = f"""
        CREATE TABLE IF NOT EXISTS "{table_name}"(
            {joined}
        );
        """
        await self._cursor.execute(sql)
        await self._connection.commit()

    async def remove_item(self, table_name: str, condition: str):
        await self._create_cursor()
        sql = f"DELETE FROM {table_name} WHERE {condition}"

        await self._cursor.execute(sql)
        await self._connection.commit()

    async def get_item(self, table_name: str, where: str=None, item_name: str=None, *, fetchall=False):
        await self._create_cursor()
        if item_name is None:
            item_name = "*"

        sql = f"SELECT {item_name} FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        await self._cursor.execute(sql)

        if fetchall:
            fetched = await self._cursor.fetchall()
        else:
            fetched = await self._cursor.fetchone()

        return fetched

    async def _create_cursor(self):
        if self._cursor is None:
            self._cursor = await self._connection.cursor()

    @classmethod
    async def from_filepath(cls, filename: PathLike):
        if isinstance(filename, pathlib.Path):
            filename = filename.resolve()
        return cls(await aiosqlite.connect(filename))

    async def __aenter__(self):
        await self._create_cursor()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        if not self.closed:
            await self._connection.commit()
            if self._cursor is not None:
                await self._cursor.close()
            await self._connection.close()
            self.closed = True

def is_blacklisted():
    connection = DatabaseWrap.from_filepath("main.db")

    async def actual(ctx):
        item = connection.get_item("blacklisteds", f"user_id = {ctx.author.id}", 'user_id')

        return item is None

    return commands.check(actual)


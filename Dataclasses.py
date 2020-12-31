import discord
import json
import os
import yaml
import sqlite3
from Utils import DatabaseWrap, Field

def write_reaction_messages_to_file(channel, message, emoji, role):
    connection = sqlite3.connect("main.db")
    cursor = connection.cursor()
    wrapp = DatabaseWrap(connection)

    if isinstance(channel, discord.TextChannel):
        channel = channel.id
    if isinstance(message, discord.Message):
        message = message.id
    if isinstance(emoji, (discord.PartialEmoji, discord.Emoji)):
        emoji = emoji.name

    fields = (
                Field(name="channel", type="TEXT"),
                Field(name="message", type="TEXT"),
                Field(name="emoji", type="TEXT"),
                Field(name="role", type="TEXT")
        )

    wrapp.create_table_if_absent("reaction_roles", fields)

    cursor.execute("INSERT INTO reaction_roles(channel, message, emoji, role) VALUES(?,?,?,?)",
                (channel, message, emoji, role))
    connection.commit()

def write_blacklist(user):

    if isinstance(user, discord.User):
        User = user.id
    blacklist_check={
	User
      }

    with open("BlackList.yaml", "s") as bl:
        yaml.safe_dump(blacklist_check, bl)

class SingleGuildData:
    """
    Dados que só são úteis em um bot de servidor único.
    """


    def get_guild_default_channel(self, guild):
        channel_id = self._get_guild_default_channel(str(guild.id))
        return guild.get_channel(channel_id)

    def walk_channels(self, client):
        channels = self.get_channels()

        for k, v in channels.items():
            guild = client.get_guild(int(k))
            yield guild.get_channel(int(v))

    @property
    def channel(self):
        return self._channel

    def get_channels(self):
        with open("config.json") as fp:
            cp = json.load(fp)
        return cp

    @channel.setter
    def channel(self, ch):
        if not isinstance(ch, discord.TextChannel):
            raise TypeError("Esperado discord.TextChannel, não um " + type(ch).__name__)
        self._channel = ch
        self._write_to_file()

    def _write_to_file(self):
        mode = "w"

        with open("config.json", mode) as b:
            cc = {
               self._channel.guild.id: self._channel.id
            }

            json.dump(cc, b, indent=4)

    def _get_guild_default_channel(self, guild_id):

        with open("config.json", "r") as fp:
            loaded = json.load(fp)

        return loaded.get(str(guild_id), None)

import discord
import json
import os

class SingleGuildData:
    """
    Dados que só são úteis em um bot de servidor único.
    """
    instance = None
    _channel: discord.TextChannel

    @classmethod
    def get_instance(cls):
        if (cls.instance is None):
            cls.instance = cls()

        return cls.instance

    def __init__(self):
        self._channel = None

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

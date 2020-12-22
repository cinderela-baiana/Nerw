import discord

class SingleGuildData:
    """
    Dados que só são úteis em um bot de servidor único.
    """
    instance = None
    _channel: discord.abc.Messageable

    @classmethod
    def get_instance(cls):
        if (cls.instance is None):
            cls.instance = cls()
        
        return cls.instance

    def __init__(self):
        self._channel = None

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, ch):
       if not isinstance(ch, discord.abc.Messageable):
           raise TypeError("Esperado discord.abc.Messageable, não " + type(ch).__name__)
       self._channel = ch
    
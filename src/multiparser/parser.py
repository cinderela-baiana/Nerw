import aiosqlite
import feedparser
import discord

from discord.ext import tasks

from io import StringIO
from html.parser import HTMLParser

class _MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def data(self):
        return self.text.getvalue()

def strip_tags(html: str) -> str:
    s = _MLStripper()
    s.feed(html)
    return s.data()

news = {}
old_news = {}

@tasks.loop(minutes=1)
async def parse_news(guild, channel, url):
    global news, old_news

    news[guild.id] = {}
    news[guild.id][channel.id] = {}

    fed = old_news.get(guild.id, {}).get(channel.id)
    if fed is None:
        old_news[guild.id][channel.id] = feedparser.parse(url)
    else:
        news[guild.id][channel.id] = feedparser.parse(url)
        if news[guild.id][channel.id] != old_news[guild.id][channel.id]:
            await _trigger_news(news[guild.id][channel.id], channel)

async def _trigger_news(entry, channel: discord.TextChannel):
    embed = discord.Embed(title=entry.title)
    embed.description = strip_tags(entry.content[0].value[:2000])
    embed.color = discord.Color.blurple()

    await channel.send(embed=embed)

class NewsParser:
    def __init__(self, guild: discord.Guild, channel: discord.TextChannel, url: str):
        self.guild = guild
        self.channel = channel
        self.url = url

        self._task = None

    def start(self):
        if self._task is not None:
            raise LookupError("Task already started (did you forget to call stop()?)")
        self._task = parse_news.start(self.guild, self.channel, self.url)

    def stop(self):
        """
        Para a tarefa que envia notícias.

        Nota: para cada stop(), deve haver uma chamada start() anterior equivalente.
        """

        if self._task is None:
            raise LookupError("start() was not called")
        self._task.cancel("Requested task stop")
        self._task = None

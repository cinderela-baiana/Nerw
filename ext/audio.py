import discord
import asyncio
import youtube_dl
import logging

from emoji import emojize
from discord.ext import commands
from Utils import HALF_HOUR_IN_SECS
from errors import VideoDurationOutOfBounds
from _audio import Playlist

logger = logging.getLogger(__name__)
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

youtube = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get("duration")
        self._current_duration = 0.0

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: youtube.extract_info(url=url, download=False))

        if "entries" in data:
            # estamos com uma playlist, e vamos pegar só o primeiro vídeo.
            data = data["entries"][0]
        if not stream:
            if data["duration"] > HALF_HOUR_IN_SECS:
                raise VideoDurationOutOfBounds
            await loop.run_in_executor(None, lambda: youtube.download([url]))

        filename = data["url"] if stream else youtube.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    async def download(self, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        future = await loop.run_in_executor(None, lambda: youtube.download([self.url]))
        return await future

    def read(self):
        ret = super().read()
        if ret:
            self._current_duration += 1
        return ret

    @property
    def current_duration(self):
        return self._current_duration * .02

    def ended(self, ctx):
        return self.current_duration == self.duration or \
            (ctx.voice_client.source == self and
             not ctx.voice_client.is_playing())

class Audio(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.currently_playing = {}
        self.queues = {}
        self.loop = asyncio.get_event_loop()
        self._condition = asyncio.Condition()

    def truncate_queue(self, ctx):
        if ctx.voice_client is None:
            return

        queue = self.queues[ctx.guild.id]
        player = queue.get_next_video()

        if player is not None:
            ctx.voice_client.play(player, after=lambda _: self.truncate_queue(ctx))

    @commands.command(aliases=["p", "pl"])
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def play(self, ctx: commands.Context, *, query: str):
        """Toca uma música via streaming.

        É mais recomendando usar esse comando no bot estável, já que
        vai ter menos chances de bufferings e travadas. Você ganha
        rapidez ao carregar a música, mas ao custo de estabilidade.
        """
        async with ctx.typing():
            try:
                player = await YTDLSource.from_url(query, stream=True)
            except IndexError: # música não existe
                return await ctx.reply(f"O termo ou URL não corresponde a nenhum vídeo." 
                                       " Tenta usar termos mais vagos na próxima vez.")

        if ctx.voice_client.source is None:
            ctx.voice_client.play(player, after=lambda _: self.truncate_queue(ctx))
        self.queue_song(ctx, player)
        thumb = data.get('thumbnail')

        async with aiohttp.ClientSession() as session:
            async with session.get(thumb) as request:
                thumbread = await request.read()
                
        colors = self.client.get_cog("Imagens").get_colors(image=thumbread)
        color = discord.Color.from_rgb(*colors[0])
        embed = discord.Embed(title="Som na caixa!", description=f"Ouvido e Tocando: **{player.title}**", url=f'https://youtube.com/watch?v={data.get("id")}', color=color)
        embed.set_image(url=thumb)                             
        await ctx.reply(embed=embed)
                              
    def queue_song(self, ctx, player):
        if self.queues.get(ctx.guild.id) is None:
            self.queues[ctx.guild.id] = Playlist()

        queue = self.queues[ctx.guild.id]
        queue.add_video(player)

    @commands.command(name="playdownload", aliases=["pd", "pld"])
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def play_download(self, ctx, *, query: str):
        """
        Toca uma música baixando ela. O tempo máximo para vídeos
        usando esse comando é de trinta minutos, para vídeos maiores,
        veja o comando `,play`.

        É mais recomendado usar esse comando no bot canário, já que
        vai ser mais rápido pra tocar (não baixar). Você ganha
        estabilidade, ao custo de rapidez.
        """
        async with ctx.typing():
            try:
                player = await YTDLSource.from_url(query)
            except IndexError: # música não existe
                return await ctx.reply(f"O termo ou URL não corresponde a nenhum vídeo." 
                                       " Tenta usar termos mais vagos na próxima vez.")

        if ctx.voice_client.source is None:
            ctx.voice_client.play(player, after=lambda _: self.truncate_queue(ctx))
        self.queue_song(ctx, player)
        thumb = data.get('thumbnail')

        async with aiohttp.ClientSession() as session:
            async with session.get(thumb) as request:
                thumbread = await request.read()
                
        colors = self.client.get_cog("Imagens").get_colors(image=thumbread)
        color = discord.Color.from_rgb(*colors[0])
        embed = discord.Embed(title="Som na caixa!", description=f"Ouvido e Tocando: **{player.title}**", url=f'https://youtube.com/watch?v={data.get("id")}', color=color)
        embed.set_image(url=thumb)                             
        await ctx.reply(embed=embed)
                              
    @commands.command(aliases=["lv", "disconnect"])
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def leave(self, ctx):
        """
        Sai do canal de voz atual.
        """
        emoji = emojize(":eject_button:", use_aliases=True)
        voice_client = ctx.voice_client
        if voice_client:
            del self.queues[ctx.guild.id]
            await voice_client.disconnect()
            return await ctx.message.add_reaction(emoji)

        await ctx.reply('Eu não estou em um canal de voz')

    @play.before_invoke
    @play_download.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                return await ctx.reply("Você não está conectado em um canal de voz.")

    @commands.command()
    async def pause(self, ctx):
        emoji = emojize(":pause_button:", use_aliases=True)
        if ctx.author in ctx.voice_client.channel.members:
            if not ctx.voice_client.is_playing():
                return await ctx.reply("Eu não estou reproduzindo nada.")
            ctx.voice_client.pause()
            await ctx.message.add_reaction(emoji)

    @commands.command()
    async def resume(self, ctx):
        emoji = emojize(":play_or_pause_button:", use_aliases=True)
        if ctx.author in ctx.voice_client.channel.members:
            if ctx.voice_client.is_playing():
                return await ctx.reply("Eu já estou reproduzindo algo.")
            ctx.voice_client.resume()
            await ctx.message.add_reaction(emoji)

    @commands.command(name="queue")
    async def get_queue(self, ctx):
        try:
            queue = self.queues[ctx.guild.id]
        except KeyError:
            return await ctx.reply("Não existe nenhuma fila de músicas nesse servidor..\n"
                                   "Tente adicionar músicas usando o comando `,play`.")

        scheme = []
        i = 0
        for video in queue:
            i += 1
            scm = f"{i}. {video.title} - {video.duration}"
            if i == 1:
                scm += " **(Atualmente reproduzindo)**"
            scheme.append(scm)
        del i
        await ctx.reply("\n".join(scheme))

def setup(client):
    client.add_cog(Audio(client))

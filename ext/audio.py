import discord
import asyncio
import youtube_dl

from discord.ext import commands
from Utils import HALF_HOUR_IN_SECS
from errors import VideoDurationOutOfBounds
from _audio import Playlist

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
    'options': '-vn'
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

    async def truncate_queue(self, ctx):
        queue = self.queues[ctx.guild.id]

        while queue.currently_playing.ended(ctx):
            player, _ = queue.get_next_video()
            if player:
                ctx.voice_client.play(player)

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
        try:
            if not ctx.guild.voice_client.is_playing():
                ctx.voice_client.play(player)

            await self.queue_song(ctx, player)
            await self.truncate_queue(ctx)
        except AttributeError:
            # pode ser meio raro, mas esse bloco é executado
            # quando alguém usa o ,leave enquanto o bot pega
            # as informações de alguma música.
            return

        await ctx.reply(f"Ouvindo e tocando: **{player.title}**")

    async def queue_song(self, ctx, player):
        if not isinstance(player, YTDLSource):
            player = YTDLSource.from_url(player)

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
            except VideoDurationOutOfBounds:
                return await ctx.reply("Eu não vou e não posso reproduzir vídeos "
                                       "com mais de 30 minutos, para isso, veja o comando `,play`.")

            ctx.voice_client.play(player, after=lambda err: print(f"Erro no player: {err}"))
            self.currently_playing[ctx.guild.id] = player, ctx.author.id
        await ctx.reply(f"Ouvindo e tocando: **{player.title}**")

    @commands.command(aliases=["lv", "disconnect"])
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def leave(self, ctx):
        """
        Sai do canal de voz atual.
        """
        voice_client = ctx.voice_client
        if voice_client:
            await voice_client.disconnect()
        else:
            await ctx.reply('Eu não estou em um canal de voz')

    @play.before_invoke
    @play_download.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                return await ctx.reply("Você não está conectado em um canal de voz.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.command()
    async def pause(self, ctx):
        if ctx.author in ctx.voice_client.channel.members:
            if not ctx.voice_client.is_playing():
                return await ctx.reply("Eu não estou reproduzindo nada.")
            ctx.voice_client.pause()
            await ctx.reply("Música pausada.")

    @commands.command()
    async def resume(self, ctx):
        if ctx.author in ctx.voice_client.channel.members:
            if ctx.voice_client.is_playing():
                return await ctx.reply("Eu já estou reproduzindo algo.")
            ctx.voice_client.resume()
            await ctx.reply("Música retomada.")


def setup(client):
    client.add_cog(Audio(client))

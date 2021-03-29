import discord
import asyncio
import youtube_dl
import logging
import aiohttp
import time

from emoji import emojize
from discord.ext import commands
from Utils import HALF_HOUR_IN_SECS
from errors import VideoDurationOutOfBounds
from ext._audio import Playlist
from Utils import CROSS_EMOJI

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
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 1'
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
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data), data

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
        self.currently_playing = None
        self.queues = {}
        self.loop = asyncio.get_event_loop()

    def truncate_queue(self, ctx):
        try:
            if ctx.voice_client is None:
                return
            queue = self.queues[ctx.guild.id]
            player = queue.get_next_video()
            data = player.data
            self.currently_playing = player
            if player is not None:
                ctx.voice_client.play(player, after=lambda _: self.truncate_queue(ctx))
            asyncio.create_task(self.embed(ctx, data, player, playing=True))
        except AttributeError:
            self.currently_playing = None

    @staticmethod
    async def in_voice_channel(ctx):
        """checa se o autor do comando está no canal de voz do bot"""
        voice = ctx.author.voice
        bot_voice = ctx.guild.voice_client
        if bot_voice:
            if voice and bot_voice and voice.channel and bot_voice.channel and voice.channel == bot_voice.channel:
                return True
            else:
                await ctx.reply(f"{CROSS_EMOJI} Você precisa estar no mesmo canal de voz que o bot para fazer isso.")
        else:
            pass

    @commands.command(aliases=["p", "pl"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def play(self, ctx: commands.Context, *, query: str):
        """Toca uma música via streaming.

        É mais recomendando usar esse comando no bot estável, já que
        vai ter menos chances de bufferings e travadas. Você ganha
        rapidez ao carregar a música, mas ao custo de estabilidade.
        """
        if await self.in_voice_channel(ctx):
            async with ctx.typing():
                try:
                    player, data = await YTDLSource.from_url(query, stream=True)
                except IndexError:
                    return await ctx.reply(f"O termo ou URL não corresponde a nenhum vídeo." 
                                           " Tenta usar termos mais vagos na próxima vez.")
            self.queue_song(ctx, player, data)
            if self.currently_playing is None:
                self.truncate_queue(ctx)
            else:
                await self.embed(ctx, data, player)

    async def embed(self, ctx, data, player, playing=False):
        thumb = data.get('thumbnail')
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb) as request:
                thumbread = await request.read()
        colors = self.client.get_cog("Imagens").get_colors(image=thumbread)
        color = discord.Color.from_rgb(*colors[0])
        if playing:
            embed = discord.Embed(title="Som na caixa!",
                                  description=f"Ouvido e Tocando: **{player.title}**",
                                  url=f'https://youtube.com/watch?v={data.get("id")}',
                                  color=color)
        else:
            embed = discord.Embed(title="Som na caixa!",
                                  description=f"Adicionado na fila: **{player.title}**",
                                  url=f'https://youtube.com/watch?v={data.get("id")}',
                                  color=color)
        embed.set_image(url=thumb)
        await ctx.send(embed=embed)

    def queue_song(self, ctx, player, *args):
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
                player, data = await YTDLSource.from_url(query, stream=False)
            except IndexError:
                return await ctx.reply(f"O termo ou URL não corresponde a nenhum vídeo." 
                                       " Tenta usar termos mais vagos na próxima vez.")

        self.queue_song(ctx, player, data)
        if self.currently_playing is None:
            self.truncate_queue(ctx)
        else:
            await self.embed(ctx, data, player)
                              
    @commands.command(aliases=["lv", "disconnect"])
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def leave(self, ctx):
        """
        Sai do canal de voz atual.
        """
        voice_client = ctx.voice_client
        if voice_client:
            if await self.in_voice_channel(ctx):
                emoji = emojize(":eject_button:", use_aliases=True)
                queue = self.queues[ctx.guild.id]
                queue.clear()
                del self.queues[ctx.guild.id]
                self.currently_playing = None
                await voice_client.disconnect()
                return await ctx.message.add_reaction(emoji)
        else:
            await ctx.reply(f"{CROSS_EMOJI} Eu não estou em um canal de voz.")

    @play.before_invoke
    @play_download.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                permissions = channel.permissions_for(ctx.me)
                if permissions.connect:
                    await ctx.author.voice.channel.connect()
                else:
                    return await ctx.reply(f"{CROSS_EMOJI} Eu não tenho permissão para conectar a este canal.")
            else:
                return await ctx.reply(f"{CROSS_EMOJI} Você não está conectado em um canal de voz.")

    @commands.command()
    async def pause(self, ctx):
        emoji = emojize(":pause_button:", use_aliases=True)
        if await self.in_voice_channel(ctx):
            if not ctx.voice_client.is_playing():
                return await ctx.reply("Eu não estou reproduzindo nada.")
            ctx.voice_client.pause()
            await ctx.message.add_reaction(emoji)

    @commands.command()
    async def resume(self, ctx):
        emoji = emojize(":play_or_pause_button:", use_aliases=True)
        if await self.in_voice_channel(ctx):
            if ctx.voice_client.is_playing():
                return await ctx.reply("Eu já estou reproduzindo algo.")
            ctx.voice_client.resume()
            await ctx.message.add_reaction(emoji)

    @commands.command(aliases=["s"])
    async def skip(self, ctx):
        if await self.in_voice_channel(ctx):
            try:
                ctx.voice_client.stop()
            except AttributeError:
                pass
            self.truncate_queue(ctx)

    @commands.command(name="queue", aliases=["q"])
    async def get_queue(self, ctx):
        try:
            queue = self.queues[ctx.guild.id]
            scm = f"1. {self.currently_playing.title} - {self.currently_playing.duration}"
        except Exception:
            return await ctx.reply("Não existe nenhuma fila de músicas nesse servidor.\n"
                                   "Tente adicionar músicas usando o comando `,play`.")
        scheme = []
        scm += " **(Atualmente reproduzindo)**"
        scheme.append(scm)
        i = 1
        for video in queue:
            video = list(video.keys())[0]
            i += 1
            scm = f"{i}. {video.title} - {video.duration}"
            scheme.append(scm)
        del i
        await ctx.reply("\n".join(scheme))


def setup(client):
    client.add_cog(Audio(client))

import discord
import asyncio
from discord.ext import commands
import youtube_dl
from Utils import HALF_HOUR_IN_SECS
from errors import VideoDurationOutOfBounds

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

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda : youtube.extract_info(url=url, download=False))

        if "entries" in data:
            # estamos com uma playlist, e vamos pegar só o primeiro vídeo.
            data = data["entries"][0]
        if not stream:
            if data["duration"] > HALF_HOUR_IN_SECS:
                raise VideoDurationOutOfBounds
            await loop.run_in_executor(None, lambda : youtube.download([url]))

        filename = data["url"] if stream else youtube.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Audio(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.client.currently_playing = {}

    @commands.command(aliases=["p", "pl"])
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def play(self, ctx, *, query: str):
        """Toca uma música via streaming.

        É mais recomendando usar esse comando no bot estável, já que
        vai ter menos chances de bufferings e travadas. Você ganha
        rapidez ao carregar a música, mas ao custo de estabilidade.
        """
        async with ctx.typing():
            player = await YTDLSource.from_url(query, stream=True)

            ctx.voice_client.play(player, after=lambda err : print(f"Erro no player: {err}"))
            self.client.currently_playing[ctx.guild.id] = player, ctx.author.id

        await ctx.reply(f"Ouvindo e tocando: **{player.title}**")

    @commands.command(name="playdownload", aliases=["pd", "pld"])
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def play_download(self, ctx, *, query : str):
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

            ctx.voice_client.play(player, after=lambda err : print(f"Erro no player: {err}"))
            self.client.currently_playing[ctx.guild.id] = player, ctx.author.id
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

def setup(client):
    client.add_cog(Audio(client))
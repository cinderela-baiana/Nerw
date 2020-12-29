import discord
import asyncio
from discord.ext import commands
import ffmpeg
import yaml
import youtube_dl
from discord import FFmpegPCMAudio
from discord.utils import get
from requests import get


with open('credentials.yaml') as t:
    credentials = yaml.safe_load(t)
client = commands.Bot(command_prefix=credentials.get("PREFIXO"), case_insensitive=True)
songs = asyncio.Queue()
play_next_song = asyncio.Event()

@client.event
async def on_ready():
    print('Bot de música iniciado')



async def audio_player_task():
    while True:
        play_next_song.clear()
        current = await songs.get()
        current.start()
        await play_next_song.wait()


def toggle_next():
    client.loop.call_soon_threadsafe(play_next_song.set)



@client.command(aliases=["p", "pl"])
async def play(ctx, *, query):
    channel = ctx.message.author.voice.channel
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    def search(query):
        with youtube_dl.YoutubeDL({'format': 'bestaudio', 'noplaylist':'True'}) as ydl:
            try: info = ydl.extract_info(query, download=False)
            except: info = ydl.extract_info("ytsearch:{}".format(query), download=False)['entries'][0]
            ctx.send('Now playing {}')
        return (info, info['formats'][0]['url'])
    
    video, source = search(query)
    
    if  channel.connect().is_connected:
         voice.play(FFmpegPCMAudio(source, **FFMPEG_OPTS), after=lambda e: print('done', e))
         voice.is_playing()
    else:
         voice = await channel.connect() 
    
    
            
@client.command(aliases=["lv", "disconnect"])
async def leave(ctx):
        connected=False
        await ctx.voice_client.disconnect()


client.loop.create_task(audio_player_task())

client.run(credentials.get("TOKEN"))

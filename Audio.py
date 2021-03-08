import discord
import asyncio
from discord.ext import commands
import ffmpeg
import yaml
import youtube_dl
from discord import FFmpegPCMAudio
from discord.utils import get
from requests import get



@client.event
async def on_ready():
    print('Script de música iniciado')


def search(query):
    with youtube_dl.YoutubeDL({'format': 'bestaudio', 'noplaylist':'True'}) as ydl:
        if query.startswith("www.") or query.startswith("https:"):
            info = ydl.extract_info(query, download=False)
        else:
            info = ydl.extract_info("ytsearch:{}".format(query), download=False)['entries'][0]
        video, source = (info, info['formats'][0]['url'])
        return source

@client.command(aliases=["p", "pl"])
async def play(ctx, *, query):
    channel = ctx.message.author.voice.channel
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    voice = channel.connect()
    
    
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice == None:
      await voice
    else:
        pass
    
        voice.play(FFmpegPCMAudio(search(query), **FFMPEG_OPTS), after=lambda e: ctx.send('Música', e))
        voice.is_playing()
    
        
          
    
    
            
@client.command(aliases=["lv", "disconnect"])
async def leave(ctx):
    server = ctx.message.server
    voice_client = client.voice_client_in(server)
    await ctx.voice_client.disconnect()
    if voice_client:
        await voice_client.disconnect()
    else:
        await ctx.send('Eu não estou em um canal de voz')




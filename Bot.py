import discord
import yaml
import asyncio
import logging
import json
import requests
import aiohttp
import sys
import traceback
import emoji
import datetime
import random
import os
import sqlite3

from Dataclasses import SingleGuildData, write_reaction_messages_to_file
from typing import Optional
from discord.ext import commands, tasks
from itertools import cycle
from Tasks import Tasks
from Utils import DatabaseWrap

apitempo = '462cc03a77176b0e983f9f0c4c192f3b'
tempourl = "http://api.openweathermap.org/data/2.5/weather?"

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.all()

# evita do bot mencionar everyone e cargos
allowed_mentions = discord.AllowedMentions(everyone = False, roles=False)


async def quit_bot(client, *, system_exit=False):
    """
    Fecha o bot.
    """
    await client.close()
    if system_exit:
        raise SystemExit


with open("config/activities.json") as fp:
    activities = cycle(json.load(fp))
with open('config/credentials.yaml') as t:
    credentials = yaml.load(t, Loader=yaml.FullLoader)
with open("config/reaction_messages.yaml") as fp:
    rm = yaml.safe_load(fp)

reaction_messages = rm
client = commands.Bot(command_prefix=credentials.get("PREFIXO"), case_insensitive=True,
                intents=intents, allowed_mentions=allowed_mentions)

client.remove_command("help")

def load_all_extensions(*, folder=None):
    """Carrega todas as extensões."""

    if folder is None:
        folder = "ext"
    filt = filter(lambda fold : fold.endswith(".py") and not fold.startswith("_"), os.listdir(folder))
    for file in filt:
        client.load_extension(f"{folder}.{file.replace('.py', '')}")

load_all_extensions()


@tasks.loop(minutes=5)
async def presence_setter():
    payload = next(activities)
    activity = discord.Activity(type=payload.get("type", 0), name=payload["name"])

    await client.change_presence(activity=activity, status=payload.get("status", "online"))
tas = Tasks(client)

@client.event
async def on_ready():
     print('Bot pronto')
     # tas.start_tasks()
     presence_setter.start()


@client.event
async def on_disconnect():
     presence_setter.stop()
     tas.stop_tasks()

@client.event
async def on_raw_reaction_add(struct):
    if struct.guild_id is None:
       return # ignorar DMs

    wrap = DatabaseWrap.from_filepath("main.db")
    item = wrap.get_item("reaction_roles", where=f"message = {struct.message_id}")
    print(item)
    if item is not None:
        channel_id, message_id, emoji, role_id = item[0]

        guild = client.get_guild(struct.guild_id)
        channel = guild.get_channel(struct.channel_id)
        member = guild.get_member(struct.user_id)
        role = guild.get_role(role_id)

        if emoji == str(struct.emoji) and message_id == struct.message_id:
            await member.add_roles(role, reason="Reaction Roles.", atomic=True)



@client.event
async def on_raw_reaction_remove(struct: discord.RawReactionActionEvent):
    if struct.guild_id is None:
        return # ignorar DMs

    wrap = DatabaseWrap.from_filepath("main.db")
    item = wrap.get_item("reaction_roles", where=f"message = {struct.message_id}")
    print(item)
    if item is not None:

        channel_id, message_id, emoji, role_id = item[0]
        guild = client.get_guild(struct.guild_id)
        channel = guild.get_channel(struct.channel_id)
        member = guild.get_member(struct.user_id)
        role = guild.get_role(int(role_id))

        print(int(message_id) == struct.message_id)
        if int(message_id) == struct.message_id:
            await member.add_roles(role, reason="Reaction Roles.", atomic=True)

@client.event
async def on_raw_reaction_remove(struct: discord.RawReactionActionEvent):
    if struct.guild_id is None:
        return # ignorar DMs

    wrap = DatabaseWrap.from_filepath("main.db")
    item = wrap.get_item("reaction_roles", where=f"message = {struct.message_id}")
    print(item)
    if item is not None:

        channel_id, message_id, emoji, role_id = item[0]
        guild = client.get_guild(struct.guild_id)
        channel = guild.get_channel(struct.channel_id)
        member = guild.get_member(struct.user_id)
        role = guild.get_role(int(role_id))

        print(int(message_id) == struct.message_id)
        if int(message_id) == struct.message_id:
            await member.remove_roles(role, reason="Reaction Roles.", atomic=True)


@client.event
async def on_message(message):
    await client.process_commands(message)


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"{ctx.author.mention} Pare. Pare imediatamente de executar este comando. Ainda faltam {int(round(error.retry_after,0))}s para você "
            "usar o comando novamente.", delete_after=5
        )
        await asyncio.sleep(5)
        await ctx.message.delete()

    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(
            f"{ctx.author.mention} usuário não encontrado.", delete_after=5)
        await ctx.message.delete()

    elif isinstance(error, commands.CommandNotFound):
        pass

    elif isinstance(error, (discord.Forbidden, commands.BotMissingPermissions)):
        embed = discord.Embed(title="Houve um erro ao executar o comando!",
                description=f"O comando `{ctx.command.name}` finalizou prematuramente"
                            " devido a minha falta de permissões. \nVerifique se eu tenho"
                            " as permissões e hierarquia de cargos corretas e tente novamente.",

                            color=discord.Color.greyple())

        if hasattr(error, "code"): # discord.Forbbiden
            embed.set_footer(text=f"Código do erro: **{error.code}**")

        elif hasattr(error, "missing_perms"): # commands.BotMissingPermissions
            missing = ", ".join(error.missing_perms)
            embed.set_footer(text=f"Permissões faltando: **{missing}**")

        await ctx.send(ctx.author.mention, embed=embed)

    else:
        descr = f"```{type(error).__name__}: {error}```"
        embed = discord.Embed(title="Houve um erro ao executar esse comando!",
                    description=descr, color=discord.Color.dark_theme())

        await ctx.send(ctx.author.mention, embed=embed)

@client.command()
async def tempo(ctx, *, cidade: str):
    """Verifica o tempo atual na sua cidade
       """
    urlcompleta = tempourl + "appid=" + apitempo + "&q=" + cidade + "&lang=pt_br"
    async with aiohttp.ClientSession() as session:
        async with session.get(urlcompleta) as request:
            x = await request.json()
            status_code = request.status

    if status_code != 404:
        async with ctx.channel.typing():
            y = x["main"]
            current_temperature = y["temp"]
            current_temperature_celsiuis = str(round(current_temperature - 273.15))
            current_pressure = y["pressure"]
            current_humidity = y["humidity"]
            z = x["weather"]
            weather_description = z[0]["description"]

            embed = discord.Embed(title=f"Tempo em {cidade}",
                              color=ctx.guild.me.top_role.color,
                              timestamp=ctx.message.created_at,)
            embed.add_field(name="Descrição", value=f"**{weather_description}**", inline=False)
            embed.add_field(name="Temperatura(C)", value=f"**{current_temperature_celsiuis}°C**", inline=False)
            embed.add_field(name="Humildade(%)", value=f"**{current_humidity}%**", inline=False)
            embed.add_field(name="Pressão atmosférica(hPa)", value=f"**{current_pressure}hPa**", inline=False)
            embed.set_thumbnail(url="https://i.ibb.co/CMrsxdX/weather.png")
            embed.set_footer(text=f"Requisitado por {ctx.author.name}")

            await ctx.channel.send(embed=embed)
    else:
        await ctx.channel.send("Cidade não encontrada.")

@client.command()
@commands.has_permissions(ban_members = True)
@commands.bot_has_permissions(ban_members = True)
async def ban(ctx, member : discord.Member, *, reason = None):
    if member == ctx.message.author:
        await ctx.channel.send("Você não pode se banir!")
        return

    embed = embed= discord.Embed(title=f"{client.get_emoji(793335773892968502)} {member} foi banido!",
                description=f"**Motivo:** *{reason}*",
                color=0x00ff9d)
    embed.set_footer(text="Não façam como ele crianças, respeitem as regras.")

    await member.ban(reason= reason)
    await ctx.channel.send(embed=embed)
    await ctx.message.delete()

@client.command()
@commands.is_owner()
async def exit(ctx):
    """Desliga o bot.

    Você precisa ser um do(s) dono(s) do bot para executar o comando.
    """
    msg = await ctx.send(f"{ctx.author.mention} Você tem certeza?")

    white_check_mark = emoji.emojize("👋")
    sos = emoji.emojize("🤙")

    await msg.add_reaction(white_check_mark)
    await msg.add_reaction(sos)
    try:
        def check(reaction, user):
            nonlocal ctx, msg
            return reaction.emoji in (white_check_mark, sos) and user == ctx.author and reaction.message == msg
        reaction, user = await client.wait_for("reaction_add", check=check, timeout=20.0)
    except asyncio.TimeoutError:
        pass
    else:
        if reaction.emoji == white_check_mark:
            await ctx.send("Ok :cry:")
            await quit_bot(client, system_exit=True)

@client.command(pass_context=True)
async def ping(ctx):
    """Verifica seu ping.
    """
    await ctx.channel.send('Pong! latência : {} ms \n https://tenor.com/KWO8.gif'.format(round(client.latency*1000, 1)))

@client.command(aliases=["channel", "sc"])
@commands.has_permissions(manage_channels=True)
async def setchannel(ctx, channel: Optional[discord.TextChannel]):
    """Define o canal padrão para as respostas principais (logs).

    Você precisa da permissão `Gerenciar Canais`.
    """
    inst = SingleGuildData.get_instance()
    inst.channel = ctx.channel if channel is None else channel
    await ctx.channel.send(embed=discord.Embed(description='Canal {} adicionado como canal principal de respostas!'.format(inst.channel.mention), color=0xff0000))

@client.command()
@commands.has_permissions(manage_channels=True)
async def reaction_activate(ctx, channel: Optional[discord.TextChannel],
        msg: str,
        emoji: discord.Emoji,
        role: discord.Role):
    """Sisteminha básico de reaction roles, atualmente suporta apenas 1 reação por mensagem."""
    message = await channel.send(msg)
    try:
        await message.add_reaction(emoji)
    except discord.InvalidArgument:
        await channel.send("Me desculpe, aparentemente há algo de errado com o seu emoji :sad:")
    except discord.NotFound:
        await channel.send("Emoji não encontrado")
    except discord.HTTPException:
        await channel.send("Algo deu errado:(")
    else:
        write_reaction_messages_to_file(channel.id, message.id, emoji.id, role.id)
        await channel.send("Mensagem reagida com sucesso!")

client.run(credentials.get("TOKEN"))

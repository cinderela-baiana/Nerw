import discord
import yaml
import asyncio
import logging
import json
import requests
from geopy.geocoders import Nominatim
import aiohttp
from discord.ext import commands, tasks, menus
import traceback
import emoji
import datetime
import random
import os
import sqlite3
import chatterbot
from datetime import timezone
from chatterbot.trainers import ChatterBotCorpusTrainer
from dataclass import SingleGuildData, write_reaction_messages_to_file, write_blacklist
from typing import Optional
from discord.ext import commands, tasks
from itertools import cycle
from Tasks import Tasks
from Utils import DatabaseWrap, Field
from chatter_thread import ChatterThread
from chatterbot import ChatBot
from errors import UserBlacklisted

apitempo = '462cc03a77176b0e983f9f0c4c192f3b'
tempourl = "https://api.openweathermap.org/data/2.5/onecall?"
geolocator = Nominatim(user_agent='joaovictor.lg020@gmail.com')

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.all()
blacklisteds = []
# evita do bot mencionar everyone e cargos
allowed_mentions = discord.AllowedMentions(everyone=False, roles=False)


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
    credentials = yaml.load(t)

client = commands.Bot(command_prefix=credentials.get("PREFIXO"), case_insensitive=True,
                      intents=intents, allowed_mentions=allowed_mentions)

client.remove_command("help")

def load_all_extensions(*, folder=None):
    """Carrega todas as extensões."""

    if folder is None:
        folder = "ext"
    filt = filter(lambda fold: fold.endswith(".py") and not fold.startswith("_"), os.listdir(folder))
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
async def on_connect():
    client.chatbot = ChatBot("Iguaçu")
    client.chat_thread = ChatterThread(client.chatbot)
    client.chat_thread.start()


@client.event
async def on_ready():
    logging.info('Bot pronto como ' + str(client.user))
    # tas.start_tasks()
    presence_setter.start()


@client.event
async def on_disconnect():
    presence_setter.stop()
    client.chat_thread.stop()

@client.check
async def blacklist(ctx):
    fields = (
  Field(name="user_id", type="TEXT NOT NULL"),
  Field(name="reason", type="TEXT")
)
    wrap = DatabaseWrap.from_filepath("main.db")
    wrap.create_table_if_absent("blacklisteds", fields)
    connection = DatabaseWrap.from_filepath("main.db")
    item = connection.get_item("blacklisteds", f"user_id = {ctx.author.id}", 'user_id')
    if item is None:
        return True
    raise UserBlacklisted

@client.event
async def on_raw_reaction_add(struct):
    if struct.guild_id is None:
       return # ignorar DMs

    wrap = DatabaseWrap.from_filepath("main.db")

    fields = (
        Field(name="channel", type="TEXT"),
        Field(name="message", type="TEXT"),
        Field(name="emoji", type="TEXT"),
        Field(name="role", type="TEXT")
    )

    wrap.create_table_if_absent("reaction_roles", fields)
    item = wrap.get_item("reaction_roles", where=f"message = {struct.message_id}")

    if item is not None:
        try:
            channel_id, message_id, emoji, role_id = item[0]
        except IndexError:
            return

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

    if item is not None:

        try:
            channel_id, message_id, emoji, role_id = item[0]
        except IndexError:
            return

        guild = client.get_guild(struct.guild_id)
        channel = guild.get_channel(struct.channel_id)
        member = guild.get_member(struct.user_id)
        role = guild.get_role(int(role_id))

        print(int(message_id) == struct.message_id)
        if int(message_id) == struct.message_id:
            await member.add_roles(role, reason="Reaction Roles.", atomic=True)

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

        if hasattr(error, "code"):  # discord.Forbbiden
            embed.set_footer(text=f"Código do erro: **{error.code}**")

        elif hasattr(error, "missing_perms"):  # commands.BotMissingPermissions
            missing = ", ".join(error.missing_perms)
            embed.set_footer(text=f"Permissões faltando: **{missing}**")

        await ctx.send(ctx.author.mention, embed=embed)

    elif isinstance(error, commands.MissingRequiredArgument):
        command = client.get_command("help")

        await ctx.invoke(command, ctx.command.name)

    elif isinstance(error, UserBlacklisted):
        connection = DatabaseWrap.from_filepath("main.db")
        reason = connection.get_item("blacklisteds", f"user_id = {ctx.author.id}", "reason")
        if reason is None:
            reason = "Nenhum..."

        await ctx.reply("Saia, você entrou pra lista negra. Motivo: **{reason}**")

    else:
        descr = f"```{type(error).__name__}: {error}```"
        embed = discord.Embed(title="Houve um erro ao executar esse comando!",
                              description=descr, color=discord.Color.dark_theme())

        await ctx.send(ctx.author.mention, embed=embed)

class Tempo(menus.Menu):
    def __init__(self, ctx, request, cidade):
        super().__init__()
        self.cidade = cidade
        self.page = 0
        self.ctx = ctx
        self.request = request

    async def get_weather(self, page):
        ctx = self.ctx
        x = self.request

        if x != 404:
            async with ctx.channel.typing():
                y = x["current"]
                d = x['daily']
                dt = datetime.datetime.utcnow()
                dt1 = datetime.datetime(dt.year, dt.month, dt.day, 1)
                dt1 = dt1 + datetime.timedelta(days= page)
                dt1 = int(dt1.timestamp())
                dt2 = datetime.datetime(dt.year, dt.month, dt.day, 23)
                dt2 = dt2 + datetime.timedelta(days= page)
                dt2 = int(dt2.timestamp())
                for item in d:
                    between = list(item.values())[1] in range(dt1, dt2)
                    if between:
                        print('oi')
                        d = item
                        pop = (item['pop'])

                if page == 0: period = y
                else: period = d

                current_temperature = period['temp']
                try:
                    current_temperature = current_temperature.get('day')
                    print(current_temperature)
                except: pass
                current_temperature_celsiuis = str(round(current_temperature - 273.15))
                current_humidity = period['humidity']
                z = period["weather"]
                weather_description = z[0]['description']
                a = x.get('alerts')
                if a != None:
                    alerts = a[0]['description']
                else:
                    alerts = 'Nenhum'
                icon = z[0]['icon']
                iconurl = f'http://openweathermap.org/img/wn/{icon}@2x.png'
                dtnow=datetime.datetime.now() + datetime.timedelta(days= page)
                embed = discord.Embed(title=f"Tempo em {self.cidade} {dtnow.day}/{dt.month}/{dt.year}",
                                      color=ctx.guild.me.top_role.color,
                                      timestamp=ctx.message.created_at, )
                embed.add_field(name="Descrição", value=f"**{weather_description.capitalize()}**", inline=False)
                embed.add_field(name="🌡️ Temperatura(C)", value=f"Média: **{current_temperature_celsiuis}°C**",
                                inline=False)
                embed.add_field(name="💦 Humildade(%)", value=f"**{current_humidity}%**", inline=False)
                embed.add_field(name="☔ Chance de chuva(%)", value=f"**{pop * 100}%**", inline=False)
                embed.add_field(name="⚠ Alertas:", value=f"**{alerts}**", inline=False)
                embed.set_thumbnail(url=iconurl)
                embed.set_footer(text=f"Requisitado por {ctx.author.name}")
                return embed

    async def send_initial_message(self, ctx, channel):
        weather = await self.get_weather(page=self.page)
        return await ctx.send(embed= weather)

    @menus.button('⬅️')
    async def on_left(self, payload):
        if not self.page == 0:
            self.page -= 1
        weather = await self.get_weather(page=self.page)
        await self.message.edit(embed=weather)

    @menus.button('➡️')
    async def on_right(self, payload):
        if not self.page == 7:
            self.page += 1
        weather = await self.get_weather(page=self.page)
        await self.message.edit(embed=weather)

@commands.cooldown(1, 20.0, commands.BucketType.member)
@client.command()
async def tempo(ctx, *, cidade: str):
    """Verifica o tempo atual na sua cidade
       """
    cidade = cidade.capitalize()

    if cidade.startswith('Cidade do'):
        cidade = 'rolândia'
    try:
        locator = geolocator.geocode(cidade)
        urlcompleta = tempourl + "lat=" + str(locator.latitude) + "&lon=" + str(
        locator.longitude) + '&appid=' + apitempo + "&lang=pt_br"
        async with aiohttp.ClientSession() as session:
            async with session.get(urlcompleta) as request:
                request = await request.json()
        w = Tempo(ctx, request, cidade)
        await w.start(ctx)
    except:
        await ctx.send("Local não encontrado")

@client.command()
@commands.cooldown(1, 20, commands.BucketType.member)
async def selfmute(ctx, seconds: int):
    message = await ctx.send("Você quando usar esse comando, fique ciente de que será mutado."
                             "\n\nNão vá na DM de nenhum Ajudante/Moderador reclamar de que não sabia que iria ser.")

    await message.add_reaction("👎")
    await message.add_reaction("👍")

    def check(reaction, user):
        return reaction.message.id == message.id and user == ctx.author and reaction.emoji in ("👍", "👎")

    try:
        reaction, user = await client.wait_for("reaction_add", check=check, timeout=60.0)
    except asyncio.TimeoutError:
        return
    else:
        role = await mute_user(ctx, ctx.author)

        await ctx.reply(":ok_hand:")
        await asyncio.sleep(seconds)
        await ctx.author.remove_roles(role)

async def mute_user(ctx, user):
    role = discord.utils.find(lambda item: item.name == "Muted", ctx.guild.roles)

    if role is None:
        role = await ctx.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))

    await user.add_roles(role)
    return role

@client.command()
@commands.has_permissions(manage_messages=True)
async def mover_mensagem(ctx, id_mensagem, canal: discord.TextChannel,*, motivo = None):
    if motivo == None:
        motivo = 'Não especificado'
    hook = await canal.create_webhook(name="Gamera Bot")
    message = await ctx.fetch_message(id_mensagem)
    print(message.attachments)
    files = None
    if message.attachments:
        files = [await att.to_file() for att in message.attachments]
    await canal.send(content = f'{message.author.mention}', embed= discord.Embed(title= f'Mensagem movida!',
                                          description= f'Sua mensagem foi movida para cá.\n'
                                                       f'Motivo: {motivo}'), delete_after= 20)
    await hook.send(content=message.content, files= files, username=message.author.name,
                    avatar_url=message.author.avatar_url)
    await message.delete()
    await ctx.message.delete()
    await hook.delete()
@client.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    if member == ctx.message.author:
        await ctx.channel.send("Você não pode se banir!")
        return
    emoji = client.get_emoji(793335773892968502)
    if emoji is None:
        emoji = "🔨"
    embed = embed = discord.Embed(title=f"{emoji} {member} foi banido!",
                                  description=f"**Motivo:** *{reason}*",
                                  color=0x00ff9d)
    embed.set_footer(text="Não façam como ele crianças, respeitem as regras.")

    await member.ban(reason=reason)
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

@client.command()
async def ping(ctx):
    """Verifica seu ping."""
    await ctx.reply(
        'Pong! latência : {} ms \n https://tenor.com/KWO8.gif'.format(round(client.latency * 1000, 1)))


@client.command(aliases=["channel", "sc"])
@commands.has_permissions(manage_channels=True)
async def setchannel(ctx, channel: Optional[discord.TextChannel]):
    """Define o canal padrão para as respostas principais (logs).
    Você precisa da permissão `Gerenciar Canais`.
    """
    if channel is None:
        channel = ctx.channel

    db = DatabaseWrap.from_filepath("main.db")
    fields = (
        Field(name="guild", type="TEXT NOT NULL"),
        Field(name="channel", type="TEXT NOT NULL")
    )

    db.create_table_if_absent("default_channels", fields=fields)
    db.cursor.execute("INSERT INTO default_channels(guild, channel) VALUES (?,?)", (ctx.guild.id, ctx.channel.id))
    db.database.commit()
    await ctx.channel.send(embed=discord.Embed(
        description='Canal {} adicionado como canal principal de respostas!'.format(channel.mention),
        color=0xff0000))


@client.command()
@commands.has_guild_permissions(manage_channels=True)
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


@client.command()
@commands.is_owner()
async def lex(ctx, *, extension: str):
    try:
        client.load_extension(f"ext.{extension}")
    except commands.ExtensionNotFound as ex:
        await ctx.reply(f"Não existe uma extensão chamada `{ex.name}`")
        return
    except commands.ExtensionAlreadyLoaded as ex:
        await ctx.reply(f"A extensão `{ex.name}` já está carregada.")
        return
    except commands.NoEntryPointError as ex:
        await ctx.reply(f"A extensão `{ex.name}` não possui a função `setup(...)`")
        return
    await ctx.reply("Extensão carregada :+1:")


@client.command()
@commands.is_owner()
async def unlex(ctx, *, extension: str):
    try:
        client.unload_extension(f"ext.{extension}")
    except commands.ExtensionNotLoaded as ex:
        await ctx.reply(f"A extensão `{ex.name}` não foi carregada ou não existe.")
        return
    await ctx.reply("Extensão descarregada :+1:")


@client.command()
@commands.is_owner()
async def blacklist(ctx, user: discord.Member, *, reason: str = None):
    """Deixa uma pessoa na lista negra"""
    fields = (
  Field(name="user_id", type="TEXT NOT NULL"),
  Field(name="reason", type="TEXT")
)
    wrap = DatabaseWrap.from_filepath("main.db")
    wrap.create_table_if_absent("blacklisteds", fields)
    await ctx.reply(f"O usuário {user} foi banido de usar o bot.")
    write_blacklist(user, reason)


client.run(credentials.get("TOKEN"))
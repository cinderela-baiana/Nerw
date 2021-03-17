import discord
import yaml
import asyncio
import logging
import json
import emoji
import os
import traceback
import sys
import psutil
import humanize
import platform

if sys.version_info >= (3, 9):
    # uma gambiarra pra corrigir um bug no SQLAlchemy.
    import time
    time.clock = time.perf_counter()

from typing import Optional
from itertools import cycle
from Utils import Field, create_async_database
from chatter_thread import ChatterThread
from errors import UserBlacklisted
from discord.ext import commands, tasks

SYSTEM_ROOT = "/"
humanize.i18n.activate("pt_BR")

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.all()
intents.typing = False
intents.integrations = False

# evita do bot mencionar everyone e cargos
allowed_mentions = discord.AllowedMentions(everyone=False, roles=False)

async def quit_bot(client):
    """
    Fecha o bot.
    """
    await client.close()


with open("config/activities.json") as fp:
    activities = cycle(json.load(fp))
with open('config/credentials.yaml') as t:
    credentials = yaml.load(t)

def is_canary():
    return credentials.get("ENVIROMENT", "CANARY") == "CANARY"

prefix = credentials.get("PREFIXO")
if is_canary():
    prefix = credentials.get("CANARY_PREFIX")

client = commands.Bot(command_prefix=commands.when_mentioned_or(prefix), case_insensitive=True,
                      intents=intents, allowed_mentions=allowed_mentions)
snipes = {}
client.remove_command("help")


def load_all_extensions(*, folder=None):
    """Carrega todas as extensões."""
    for ext in get_all_extensions(folder=folder):
        client.load_extension(ext)

def get_all_extensions(*, folder=None):
    if folder is None:
        folder = "ext"
    filt = filter(lambda fold: fold.endswith(".py") and not fold.startswith("_"), os.listdir(folder))
    for file in filt:
        r = f"{folder}.{file.replace('.py', '')}"
        yield r

load_all_extensions()

try:
    client.load_extension("jishaku")
except (commands.ExtensionNotFound):
    pass

@tasks.loop(minutes=5)
async def presence_setter():
    payload = next(activities)
    status = payload.get("status", "online")
    ack_type = payload.get("type", 0)
    name = payload["name"]
    if client.activity is not None:
        if client.activity.name == name:
            return

    activity = discord.Activity(type=ack_type, name=name)
    await client.change_presence(activity=activity, status=status)

@tasks.loop(minutes=2)
async def remove_snipes():
    # limpar os snipes.
    for k, v in snipes.items():
        try:
            v.pop()
        except IndexError:
            pass

@client.event
async def on_ready():
    logging.info('Bot pronto como ' + str(client.user) + " (" + str(client.user.id) + ")")
    if not hasattr(client, "chat_thread"):
        client.chat_thread = ChatterThread()
        client.chat_thread.start()
        
    client.last_statements = {}
    presence_setter.start()
    remove_snipes.start()

@client.event
async def on_disconnect():
    presence_setter.stop()
    client.chat_thread.close()
    remove_snipes.stop()

@client.event
async def on_resume():
    client.chat_thread.start()
    presence_setter.start()
    remove_snipes.start()

@client.event
async def on_message_delete(message):
    snipes_channel = snipes.get(message.channel.id)
    if snipes_channel is None:
        snipes[message.channel.id] = []
    snipes[message.channel.id].append(message)

@client.event
async def on_guild_join(guild: discord.Guild):
    suppg = client.get_guild(790744527450800139)
    qtnchan = suppg.get_channel(815313065909682178)

    if suppg is None or qtnchan is None:
        logging.warning("Eu não estou no servidor do bot ou "
                        "o canal de voz com os servidores não exite mais!")
        return

    await qtnchan.edit(name=f"Qtn. de servidores: {len(client.guilds)}")

@client.event
async def on_guild_remove(guild: discord.Guild):
    suppg = client.get_guild(790744527450800139)
    qtnchan = suppg.get_channel(815313065909682178)

    if suppg is None or qtnchan is None:
        logging.warning("Eu não estou no servidor do bot ou "
                        "o canal de voz com os servidores não exite mais!")
        return

    await qtnchan.edit(name=f"Qtn. de servidores: {len(client.guilds)}")

@client.check
async def blacklist(ctx):
    fields = (
        Field(name="user_id", type="TEXT NOT NULL"),
        Field(name="reason", type="TEXT")
    )
    async with create_async_database("main.db") as wrap:
        await wrap.create_table_if_absent("blacklisteds", fields)
        item = await wrap.get_item("blacklisteds", f"user_id = {ctx.author.id}", 'user_id')

    if item is None:
        return True
    raise UserBlacklisted

@client.event
async def on_raw_reaction_add(struct):
    if struct.guild_id is None:
        return None  # ignorar DMs

    async with create_async_database("main.db") as wrap:
        fields = (
            Field(name="channel", type="TEXT"),
            Field(name="message", type="TEXT"),
            Field(name="emoji", type="TEXT"),
            Field(name="role", type="TEXT")
        )

        await wrap.create_table_if_absent("reaction_roles", fields)
        item = await wrap.get_item("reaction_roles", where=f"message = {struct.message_id}")

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
        return None  # ignorar DMs

    async with create_async_database("main.db") as wrap:

        fields = (
            Field(name="channel", type="TEXT"),
            Field(name="message", type="TEXT"),
            Field(name="emoji", type="TEXT"),
            Field(name="role", type="TEXT")
        )

        await wrap.create_table_if_absent("reaction_roles", fields)
        item = await wrap.get_item("reaction_roles", where=f"message = {struct.message_id}")

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
                await member.remove_roles(role, reason="Reaction Roles.", atomic=True)

@client.event
async def on_message(message):
    await client.process_commands(message)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"{ctx.author.mention} Pare. Pare imediatamente de executar este comando. Ainda faltam {int(round(error.retry_after, 0))}s para você "
            "usar o comando novamente.", delete_after=error.retry_after
        )
        await asyncio.sleep(error.retry_after)
        await ctx.message.delete()
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(f"{ctx.author.mention} usuário não encontrado.", delete_after=5)
        await ctx.message.delete()
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.BotMissingPermissions):
        missing = ", ".join(map(lambda perm : "`perm`", error.missing_perms))
        await ctx.reply(f"{ctx.author.mention} Eu não tenho a(s) permissão(ões) {missing}")
    elif isinstance(error, commands.MissingRequiredArgument):
        command = client.get_command("help")
        await ctx.invoke(command, cmd=ctx.command.name)
    elif isinstance(error, commands.DisabledCommand):
        await ctx.reply(f"Desculpe, mas o comando **{ctx.command.qualified_name}** está temporariamente desabilitado.")
    elif isinstance(error, commands.MissingPermissions):
        missing = ", ".join(error.missing_perms)
        await ctx.reply(f"Você não tem as seguintes permissões: `{missing}`")
    elif isinstance(error, UserBlacklisted):
        async with create_async_database("main.db") as connection:
            reason = await connection.get_item("blacklisteds", f"user_id = {ctx.author.id}", "reason")
            try:
                reason = reason[0]
            except (IndexError, TypeError):  # não tem um motivo
                reason = "Nenhum..."

        await ctx.reply(f"Saia, você entrou pra lista negra. Motivo: **{reason}**")
    elif isinstance(error, commands.NotOwner):
        await ctx.reply("Este comando está reservado apenas para pessoas especiais. :3")
    else:
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        descr = f"```{type(error).__name__}: {error}```"
        embed = discord.Embed(title="Houve um erro ao executar esse comando!",
                              description=descr, color=discord.Color.dark_theme())

        await ctx.send(ctx.author.mention, embed=embed)

@client.command(hidden=True)
@commands.is_owner()
async def refqtn(ctx):
    suppg = client.get_guild(790744527450800139)
    qtnchan = suppg.get_channel(815313065909682178)

    if suppg is None or qtnchan is None:
        logging.warning("Eu não estou no servidor do bot ou "
                        "o canal de voz com os servidores não exite mais!")
        return

    await qtnchan.edit(name=f"Qtn. de servidores: {len(client.guilds)}")
    scheme = []
    for guild in client.guilds:
        scheme.append(guild.name)
    await ctx.reply("\n".join(scheme))

@client.command()
@commands.cooldown(2, 5, commands.BucketType.channel)
async def snipe(ctx):
    snipe_arr = snipes.get(ctx.channel.id)
    if snipe_arr is None:
        return await ctx.reply("Não existe nenhum snipe.")
    try:
        snipe = snipe_arr[len(snipe_arr) - 1]
    except IndexError:
        return await ctx.reply("Não existe nenhum snipe.")

    embed = discord.Embed(description=snipe.content, color=snipe.author.color)
    embed.set_author(name=snipe.author, icon_url=snipe.author.avatar_url)
    if snipe.attachments:
        embed.set_image(url=snipe.attachments[0].proxy_url)
    await ctx.reply(embed=embed)

@client.command()
@commands.cooldown(1, 5, commands.BucketType.member)
async def botinfo(ctx):
    cpu_percent = psutil.cpu_percent(None, percpu=True)
    threads = []
    for thread in range(0, len(cpu_percent)):
        percent = cpu_percent[thread - 1]
        threads.append(f"Núcleo {thread + 1}: {percent:.1f}%")
    threads = "\n".join(threads)

    memory = psutil.virtual_memory()

    natural_used = humanize.filesize.naturalsize(memory.used)
    natural_free = humanize.filesize.naturalsize(memory.total)
    memstr = f"{natural_used}/{natural_free}"

    hdd = psutil.disk_usage(SYSTEM_ROOT)
    hum_hdd_free = humanize.filesize.naturalsize(hdd.used)
    hum_hdd_busy = humanize.filesize.naturalsize(hdd.total)

    embed = discord.Embed(title="Informações técnicas sobre o bot.", color=discord.Color.orange())
    embed.description = "Veja o meu [código fonte](https://github.com/joao-0213/BotGamera)."

    embed.add_field(name="Porcentagem de uso dos núcleos", value=threads, inline=True)
    embed.add_field(name="Memória RAM", value=memstr, inline=True)
    embed.add_field(name="Disco Rígido", value=f"{hum_hdd_free} usados de {hum_hdd_busy}")
    embed.add_field(name="Quantidade de servidores em que o bot está", value=str(len(client.guilds)), inline=False)
    embed.add_field(name="Versão do Python", value=f"Python {platform.python_version()}")
    embed.add_field(name="Versão do discord.py", value=f"discord.py {discord.__version__}")
    embed.add_field(name="Sistema operacional atual", value=platform.platform())
    await ctx.reply(embed=embed)

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
            await quit_bot(client)

@client.command()
async def ping(ctx):
    """Verifica seu ping."""
    lat = round(client.latency * 1000, 1)
    await ctx.reply(f'Pong! latência : {lat} ms \n https://giphy.com/gifs/tennis-4IAzyrhy9rkis')

@client.command(aliases=["channel", "sc"])
@commands.has_permissions(manage_channels=True)
async def setchannel(ctx, channel: Optional[discord.TextChannel]):
    """Define o canal padrão para as respostas principais (logs).
    Você precisa da permissão `Gerenciar Canais`.
    """
    if channel is None:
        channel = ctx.channel

    async with create_async_database("main.db") as db:
        fields = (
            Field(name="guild", type="TEXT NOT NULL"),
            Field(name="channel", type="TEXT NOT NULL")
        )

        await db.create_table_if_absent("default_channels", fields=fields)
        db._cursor.execute("INSERT INTO default_channels(guild, channel) VALUES (?,?)", (ctx.guild.id, ctx.channel.id))
        db._connection.commit()
    await ctx.channel.send(embed=discord.Embed(
        description='Canal {} adicionado como canal principal de respostas!'.format(channel.mention),
        color=0xff0000))

@client.command(hidden=True)
@commands.is_owner()
async def lex(ctx, *, extension: str):
    """Carrega uma extensão."""

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

@client.command(hidden=True)
@commands.is_owner()
async def unlex(ctx, *, extension: str):
    """Descarrega uma extensão."""

    try:
        client.unload_extension(f"ext.{extension}")
    except commands.ExtensionNotLoaded as ex:
        await ctx.reply(f"A extensão `{ex.name}` não foi carregada ou não existe.")
        return
    await ctx.reply("Extensão descarregada :+1:")

@client.command(aliases=["relax"], hidden=True)
@commands.is_owner()
async def relex(ctx, extension: str):
    """Recarrega uma extensão."""
    try:
        client.reload_extension(f"ext.{extension}")
    except commands.ExtensionNotLoaded as ex:
        await ctx.reply(f"A extensão `{ex.name}` não foi carregada ou não existe.")
        return
    await ctx.reply("Extensão recarregada :+1:")

@client.command(hidden=True)
@commands.is_owner()
async def extstatus(ctx):
    """Vê o status de todas as extensões do bot."""
    schemes = []
    for ext in get_all_extensions():
        possible_extension = client.extensions.get(ext)
        extension_status = "Carregado" if possible_extension is not None else "Descarregado"
        schemes.append(f"`{ext}` - {extension_status}")

    await ctx.reply("\n".join(schemes))

token = credentials.get("CANARY_TOKEN") if is_canary() else credentials.get("TOKEN")
client.run(token)

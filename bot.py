﻿import discord
import yaml
import asyncio
import logging
import json
import emoji
import os
import traceback
import sys

from dataclass import write_reaction_messages_to_file
from typing import Optional
from itertools import cycle
from Utils import Field, create_async_database
from chatter_thread import ChatterThread
from errors import UserBlacklisted
from discord.ext import commands, tasks

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
    return credentials.get("ENVIROMENT", "STABLE") == "CANARY"

prefix = credentials.get("PREFIXO")
if is_canary():
    prefix = credentials.get("CANARY_PREFIX")

client = commands.Bot(command_prefix=commands.when_mentioned_or(prefix), case_insensitive=True,
                      intents=intents, allowed_mentions=allowed_mentions)
snipes = {}
client.remove_command("help")


def load_all_extensions(*, folder=None):
    """Carrega todas as extensões."""

    if folder is None:
        folder = "ext"
    filt = filter(lambda fold: fold.endswith(".py") and not fold.startswith("_"), os.listdir(folder))
    for file in filt:
        r = f"{folder}.{file.replace('.py', '')}"
        client.load_extension(r)


load_all_extensions()

@tasks.loop(minutes=5)
async def presence_setter():
    payload = next(activities)
    activity = discord.Activity(type=payload.get("type", 0), name=payload["name"])
    await client.change_presence(activity=activity, status=payload.get("status", "online"))

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
    logging.info('Bot pronto como ' + str(client.user) + "  (" + str(client.user.id) + ")")
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

    elif isinstance(error, commands.DisabledCommand):
        await ctx.reply("O comando está desabilitado.")

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


@client.command()
@commands.cooldown(1, 20, commands.BucketType.member)
async def selfmute(ctx, seconds: int):
    message = await ctx.send("Você quando usar esse comando, fique ciente de que será mutado."
                             "\n\nNão vá na DM de nenhum Ajudante/Moderador reclamar de que não sabia que iria ser.")

    await message.add_reaction("👍")
    await message.add_reaction("👎")

    def check(reaction, user):
        return reaction.message.id == message.id and user == ctx.author and reaction.emoji in ("👍", "👎")

    try:
        reaction, user = await client.wait_for("reaction_add", check=check, timeout=60.0)
    except asyncio.TimeoutError:
        return
    else:
        if reaction.emoji == "👍":
            role = await mute_user(ctx, ctx.author)

            await ctx.reply(":ok_hand:")
            await asyncio.sleep(seconds)
            await ctx.author.remove_roles(role)
        else:
            await ctx.reply("Comando cancelado.")


async def mute_user(ctx, user):
    role = discord.utils.find(lambda item: item.name == "Muted", ctx.guild.roles)

    if role is None:
        role = await ctx.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))

    await user.add_roles(role)
    return role


@client.command()
@commands.cooldown(2, 5, commands.BucketType.channel)
async def snipe(ctx):
    snipe_arr = snipes.get(ctx.channel.id)
    if snipe_arr is None:
        return await ctx.send("Não existe nenhum snipe.")
    snipe = snipe_arr[len(snipe_arr) - 1]

    embed = discord.Embed(description=snipe.content, color=snipe.author.color)
    embed.set_author(name=snipe.author, icon_url=snipe.author.avatar_url)

    await ctx.reply(embed=embed)


@client.command(aliases=["mov"])
@commands.has_permissions(manage_messages=True)
async def mover_mensagem(ctx, message: discord.Message, canal: discord.TextChannel, *, motivo=None):
    if motivo is None:
        motivo = 'Não especificado'

    hook = await canal.create_webhook(name="Gamera Bot")
    files = None
    if message.attachments:
        files = [await att.to_file() for att in message.attachments]
    await canal.send(content=f'{message.author.mention}', embed=discord.Embed(title=f'Mensagem movida!',
                                                description=f'Sua mensagem foi movida para cá.\n'
                                                f'Motivo: {motivo}'),
                                                delete_after=20)
    content = message.content
    if message.reference is not None and \
            not isinstance(message.reference, discord.DeletedReferencedMessage):
        # respondeu a alguém usando o novo sistema e
        # a mensagem referenciada não foi apagada

        rmessage = await ctx.channel.fetch_message(message.reference.message_id)

        files = []
        for attch in message.attachments:
            files.append(await attch.to_file())

        wmessage = await hook.send(username=rmessage.author.display_name,
                        avatar_url=rmessage.author.avatar_url,
                        content=rmessage.content,
                        files=files,
                        wait=True)

        content = f"> {wmessage.content}\n{rmessage.author.mention} {message.content}"

    await hook.send(content=content, files=files, username=message.author.name,
                    avatar_url=message.author.avatar_url)

    await message.delete()
    await ctx.message.delete()
    await hook.delete()


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


@client.command()
@commands.is_owner()
async def unlex(ctx, *, extension: str):
    try:
        client.unload_extension(f"ext.{extension}")
    except commands.ExtensionNotLoaded as ex:
        await ctx.reply(f"A extensão `{ex.name}` não foi carregada ou não existe.")
        return
    await ctx.reply("Extensão descarregada :+1:")

token = credentials.get("CANARY_TOKEN") if is_canary() else credentials.get("TOKEN")
client.run(token)

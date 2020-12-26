import discord
from Dataclasses import SingleGuildData, write_reaction_messages_to_file
from typing import Optional
import yaml
import asyncio
import logging
import json
from discord.ext import commands, tasks
from itertools import cycle
from Tasks import Tasks
import sys
import traceback
import emoji

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.all()

async def quit_bot(client, *, system_exit=False):
    """
    Fecha o bot.
    """
    await client.close()
    if system_exit:
        raise SystemExit


with open("activities.json") as fp:
    activities = cycle(json.load(fp))
with open('credentials.yaml') as t:
    credentials = yaml.load(t, Loader=yaml.FullLoader)
with open("reaction_messages.yaml") as fp:
    rm = yaml.safe_load(fp)

reaction_messages = rm
client = commands.Bot(command_prefix=credentials.get("PREFIXO"), case_insensitive=True,
    intents=intents)


@tasks.loop(minutes=5)
async def presence_setter():
    payload = next(activities)
    activity = discord.Activity(type=payload.get("type", 0), name=payload["name"])

    await client.change_presence(activity=activity, status=payload.get("status", 0))
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
    if struct.message_id in reaction_messages.keys():
        role = client.get_guild(struct.guild_id).get_role(reaction_messages[struct.message_id])

        await struct.member.add_roles(role, atomic=True)


@client.event
async def on_raw_reaction_remove(struct):
    if struct.message_id in reaction_messages.keys():
        guild = client.get_guild(struct.guild_id)
        role = guild.get_role(reaction_messages[struct.message_id])
        member = guild.get_member(struct.user_id)
        await member.remove_roles(role, atomic=True)

@client.event
async def on_message(message):
    # canal para o qual vai ser enviado o log da mensagem DM
    el = SingleGuildData.get_instance()

    # verifica se o canal de envio foi escolhido, se a mensagem é na DM e envia um embed para o canal escolhido
    if message.guild == None and not message.author.bot:
        for channel in el.walk_channels(client):
            embed = discord.Embed(title="Mensagem enviada para a DM do bot", description=message.content,
                                  color=0xff0000)
            embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
            files = []
            if hasattr(message, "attachments"):
                files = [await att.to_file() for att in message.attachments]

            await channel.send(embed=embed, files=files)

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

    elif isinstance(error, discord.ext.commands.MemberNotFound):
        await ctx.send(
            f"{ctx.author.mention} usuário não encontrado.", delete_after=5)
        await ctx.message.delete()

    else:
        descr = f"```{type(error).__name__}: {error}```"
        embed = discord.Embed(title="Houve um erro ao executar esse commando!",
                    description=descr, color=discord.Color.dark_theme())

        await ctx.send(ctx.author.mention, embed=embed)

@client.command()
async def exit(ctx):
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
@commands.cooldown(1, 120.0, commands.BucketType.guild)
async def textão(ctx):
    with ctx.typing():
        await asyncio.sleep(120)
    await ctx.channel.send("lacrei manas")
    await ctx.message.delete()

@client.command(pass_context=True)
async def ping(ctx):
   #Projeto de latência
   await ctx.channel.send('Pong! latência : {} ms \n https://tenor.com/KWO8.gif'.format(round(client.latency*1000, 1)))

@client.command()
@commands.cooldown(1, 10.0, commands.BucketType.member)
# envia uma mensagem para a dm da pessoa mencionada, um embed ensinando a responder e deleta a mensagem do comando
async def enviar(ctx, user: discord.Member, *, msg: str):
    """Envia uma mensagem para a dm da pessoa mencionada.
       é necessário de que a DM dela esteja aberta.
       """
    try:
        files = [await att.to_file() for att in ctx.message.attachments]
        await user.send(msg, files=files)
        await user.send(embed=discord.Embed(title="Responda seu amigo (ou inimigo) anônimo!",
                                        description="Para responder use `,responder <mensagem>`",
                                        color=0xff0000))
        await ctx.message.delete()

    except discord.HTTPException:
        await ctx.message.delete()
        await ctx.send("{} A mensagem não pode ser enviada. Talvez o usuário esteja com a DM bloqueada.".format(ctx.author.mention), delete_after=10)

    def check(message):
        msgcon = message.content.startswith(f"{credentials.get('PREFIXO')}responder")
        return message.author.id == user.id and message.guild is None and msgcon

        # como levar ratelimit passo-a-passo

    try:
        message = await client.wait_for("message",
                                        check=check,
                                        timeout=300.0)
    except asyncio.TimeoutError:
        await user.send("Oh não! VocÊ demorou muito para responder. :sad:")
        pass
    else:
        con = " ".join(message.content.split(" ")[1:])

        embed = discord.Embed(
            title=f"E ele respondeu!",
            color=discord.Color.red(),
            description=con,
        )
        await message.add_reaction("👍")
        embed.set_author(name=str(user), icon_url=message.author.avatar_url)
        files = None
        if message.attachments:
            files = [await att.to_file() for att in message.attachments]

        await ctx.author.send(embed=embed, files=files)

@commands.command(hidden=True)
async def temp(ctx):
    raise NotImplementedError("Este")

@client.command(name='status')
async def status(ctx, user: discord.Member):
    await ctx.channel.send(str(user.status))


@client.command()
# manda oi pra pessoa
async def oibot(ctx):
    """Tá carente? Usa esse comando!
    """
    await ctx.channel.send('Oieeeeee {}!'.format(ctx.message.author.name))


@client.command(aliases=["channel", "sc"])
@commands.has_permissions(manage_channels=True)
async def setchannel(ctx, channel: Optional[discord.TextChannel]):

    inst = SingleGuildData.get_instance()
    inst.channel = ctx.channel if channel is None else channel
    await ctx.channel.send(embed=discord.Embed(description='Canal {} adicionado como canal principal de respostas!'.format(inst.channel.mention), color=0xff0000))

@client.command()
@commands.has_permissions(manage_channels=True)
async def reaction_activate(ctx, channel: Optional[discord.TextChannel],
        msg: str,
        emoji: discord.Emoji,
        role: discord.Role):
    """Reaction roles, yay """
    channel = channel if channel is not None else \
                SingleGuildData.get_instance().get_guild_default_channel(ctx.guild.id)
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
        write_reaction_messages_to_file(channel, message, emoji)
        await channel.send("Mensagem reagida com sucesso!")

client.run(credentials.get("TOKEN"))

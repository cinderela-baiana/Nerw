import discord
from Dataclasses import SingleGuildData, write_reaction_messages_to_file
from typing import Optional
import yaml
import asyncio
import logging
import json
import requests
import aiohttp
from discord.ext import commands, tasks
from itertools import cycle
from Tasks import Tasks
import sys
import traceback
import emoji
import datetime


apitempo = '462cc03a77176b0e983f9f0c4c192f3b'
tempourl = "http://api.openweathermap.org/data/2.5/weather?"

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
client.remove_command("help")


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
    with open("reaction_messages.yaml") as fp:
        rm = yaml.safe_load(fp)
        reaction_messages = rm
        rmid = reaction_messages[struct.message_id]
        rmemoji = (list(rmid.keys())[0])
    if struct.message_id in reaction_messages.keys() and struct.emoji == client.get_emoji(rmemoji) and struct.member.id != client.user.id:
        print(reaction_messages)
        rmid = (list(rmid.values())[0])
        print(rmid)
        role = client.get_guild(struct.guild_id).get_role(rmid)
        print(role)
        await struct.member.add_roles(role, atomic=True)


@client.event
async def on_raw_reaction_remove(struct):
    with open("reaction_messages.yaml") as fp:
        rm = yaml.safe_load(fp)
        reaction_messages = rm
        guild = client.get_guild(struct.guild_id)
        rmid = reaction_messages[struct.message_id]
        rmemoji = (list(rmid.keys())[0])
    if struct.message_id in reaction_messages.keys() and struct.emoji == client.get_emoji(rmemoji):
        rmid = (list(rmid.values())[0])
        role = guild.get_role(rmid)
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

    if client.user in message.mentions and message.content == '<@790594153629220894>':
        await message.channel.send(f"{message.author.mention} Oi, meu prefixo é `{credentials.get('PREFIXO')}`")

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
                            " as permissões corretas e tente novamente.",

                            color=discord.Color.greyple())
        if hasattr(error, "code"): # discord.Forbbiden
            embed.set_footer(text=f"Código do erro: **{error.code}**")
        else: # commands.BotMissingPermissions
            missing = ", ".join(error.missing_perms)
            embed.set_footer(text=f"Permissões faltando: {missing}")

        await ctx.send(ctx.author.mention, embed=embed)

    else:
        descr = f"```{type(error).__name__}: {error}```"
        embed = discord.Embed(title="Houve um erro ao executar esse comando!",
                    description=descr, color=discord.Color.dark_theme())

        await ctx.send(ctx.author.mention, embed=embed)

client.load_extension("Custom_modules")


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

@client.command()
@commands.cooldown(1, 120.0, commands.BucketType.guild)
async def textão(ctx):
    """Faz um textão do tamanho do pinto do João."""
    with ctx.typing():
        await asyncio.sleep(120)
    await ctx.channel.send("lacrei manas")
    await ctx.message.delete()

@client.command(pass_context=True)
async def ping(ctx):
    """Verifica seu ping.
    """
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

    guild = client.get_guild(790744527450800139)
    channel = guild.get_channel(790744527941009480)

    enviar_embed = discord.Embed(title=",enviar usado.", description=ctx.message.content,
                        color=discord.Color.red())
    enviar_embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
    await channel.send(embed=enviar_embed)


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

@client.command()
# manda oi pra pessoa
async def oibot(ctx):
    """Tá carente? Usa esse comando!"""
    await ctx.channel.send('Oieeeeee {}!'.format(ctx.message.author.name))


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
        write_reaction_messages_to_file(message.id, emoji.id, role.id)
        await channel.send("Mensagem reagida com sucesso!")

client.run(credentials.get("TOKEN"))

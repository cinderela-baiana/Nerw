import discord
import yaml
import asyncio
import logging
import json

from Dataclasses import SingleGuildData
from typing import Optional
from discord.ext import commands, tasks
from itertools import cycle

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.all()
with open("activities.json") as fp:
    activities = cycle(json.load(fp))
with open('credentials.yaml') as t:
    credentials = yaml.load(t, Loader=yaml.FullLoader)

client = commands.Bot(command_prefix=credentials.get("PREFIXO"), case_insensitive=True,
    intents=intents)

@tasks.loop(minutes=5)
async def presence_setter():
    payload = next(activities)
    print(payload, activities)
    activity = discord.Activity(type=payload.get("type", 0), name=payload["name"])

    await client.change_presence(activity=activity, status=payload.get("status", 0))


@client.event
async def on_ready():
    print('Bot pronto')
    presence_setter.start()

@client.event
async def on_disconnect():
    presence_setter.stop()

@client.event
async def on_message(message):
    # canal para o qual vai ser enviado o log da mensagem DM
    el = SingleGuildData.get_instance()
    # verifica se o canal de envio foi escolhido, se a mensagem é na DM e envia um embed para o canal escolhido
    if message.guild == None and not message.author.bot:
        for channel in el.walk_channels(client):
            embed = discord.Embed(title="Mensagem enviada para a DM do bot", description= message.content, color=0xff0000)
            embed.set_author(name= message.author.name, icon_url= message.author.avatar_url)
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
            "usar o comando novamente."
        )
    else:
        print(error)

@client.command(pass_context=True)
async def ping(ctx):
   #Projeto de latência
   await ctx.channel.send('Pong! lantência : {} ms \n https://tenor.com/KWO8.gif'.format(round(client.latency*1000, 1)))

@client.command()
@commands.cooldown(1, 10.0, commands.BucketType.member)
# envia uma mensagem para a dm da pessoa mencionada, um embed ensinando a responder e deleta a mensagem do comando
async def dm(ctx, user: discord.Member, *, msg: str):
    """Envia uma mensagem para a dm da pessoa mencionada.
       é necessário de que a DM dela esteja aberta.
       """
    await user.send(msg)
    await user.send(embed=discord.Embed(title="Responda seu amigo (ou inimigo) anônimo!",
                                        description="Para responder use `,responder <mensagem>`",
                                        color=0xff0000))
    await ctx.message.delete()

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


        embed.set_author(name=str(user), icon_url=message.author.avatar_url)
        channel = SingleGuildData.get_instance().get_guild_default_channel(credentials.get("SUPPORT_GUILD_ID"))
        attachments = None
        if hasattr(message, "attachments"):
            attachments = "\n".join([attach.to_file() for attach in message.attachments])

        try:
            await ctx.author.send(embed=embed, files=attachments if attachments is not None else [])
        except Exception as e:
            
            if channel is not None:
                await channel.send("Algo deu errado durante o ,responder! ", 
                    embed=discord.Embed(description="```" + str(e) + "```"))
        else:
            if channel is not None:
                await channel.send("Tudo certo durante o ,responder!")

@client.command()
# estranho
async def uiui(ctx):
    """o-onichan :flush:
    """
    await ctx.channel.send('gozei')


@client.command()
# manda oi pra pessoa
async def oibot(ctx):
    """Tá carente? Usa esse comando!
    """
    for member in client.get_all_members():
        print(member)
    await ctx.channel.send('Oieeeeee {}!'.format(ctx.message.author.name))

@client.command(aliases=["channel", "sc"])
@commands.has_permissions(manage_channels=True)
async def setchannel(ctx, channel: Optional[discord.TextChannel]):

    inst = SingleGuildData.get_instance()
    inst.channel = ctx.channel if channel is None else channel
    await ctx.channel.send(embed=discord.Embed(description='Canal {} adicionado como canal principal de respostas!'.format(inst.channel.mention), color=0xff0000))

                                            #Rodovia, na moral para com esses comentários, só para...


@commands.has_permissions(manage_channels=True)
async def reaction_activate(ctx, msg:str, emoji:Discord.Emoji):
    """Reaction roles, yay """
    await client.channel.send(msg)
    try:
	    await add_reaction(emoji)
    except InvalidArgument:
	    await channel.send("Me desculpe, aparentemente há algo de errado com o seu emoji :sad:")
    except NotFound:
	    await channel.send("Emoji não encontrado")
    except HTTPException:
	    await channel.send("Algo deu errado:(")
    else:
	    await channel.send("Mensagem reagida com sucesso!")

client.run(credentials.get("TOKEN"))

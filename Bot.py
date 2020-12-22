import discord
from Dataclasses import SingleGuildData
from typing import Optional
import yaml
import asyncio
from discord.ext import commands

with open('credentials.yaml') as t:
    credentials = yaml.load(t, Loader=yaml.FullLoader)

client = commands.Bot(command_prefix=credentials.get("PREFIXO"), case_insensitive=True)

@client.event
async def on_ready():
    print("Bot pronto.")

@client.event
async def on_message(message: discord.Message):
    # canal para o qual vai ser enviado o log da mensagem DM
    el = SingleGuildData.get_instance().channel

    # verifica se o canal de envio foi escolhido, se a mensagem é na DM e envia um embed para o canal escolhido
    if message.guild == None and not el == None and not message.author.bot:
        embed = discord.Embed(title="Mensagem enviada para a DM do bot", 
        description= message.content, 
        color=0xff0000)
        embed.set_author(name= message.author.name, icon_url= message.author.avatar_url)
        await el.send(embed=embed)

    if client.user.mentioned_in(message):
        await message.channel.send(f"{message.author.mention} oi hihihi, meu prefixo é `{credentials.get('PREFIXO')}`.")

    await client.process_commands(message)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"{ctx.author.mention} Pare. Pare imediatamente de executar este comando, ainda falta {error.retry_after} para você "
            "usar o comando novamente."
            )


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

    def check(message):
        msgcon =  message.content.startswith(f"{credentials.get('PREFIXO')}responder")
        return message.author.id == user.id and message.guild is None and msgcon

    # como levar ratelimit passo-a-passo
    try:
        message = await client.wait_for("message", 
        check=check, 
        timeout=30.0)
    except asyncio.TimeoutError:
        pass
    else:
        con = " ".join(message.content.split(" ")[1:])
        
        embed = discord.Embed(
            title=f"E ele respondeu!",
            color=discord.Color.red(),
            description=con,
        )

        embed.set_author(name=str(user), icon_url=message.author.avatar_url)
        await ctx.author.send(embed=embed)

    await ctx.message.delete()

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
    await ctx.channel.send('Oieeeeee {}!'.format(ctx.message.author.name))

@client.command(aliases=["channel", "sc"])
@commands.has_permissions(manage_channels=True)
async def setchannel(ctx, channel: Optional[discord.TextChannel]):

    inst = SingleGuildData.get_instance()
    inst.channel = ctx.channel if channel is None else channel
    await ctx.channel.send(embed=discord.Embed(description='Canal {} adicionado como canal principal de respostas!'.format(inst.channel.mention), color=0xff0000))

client.run(credentials.get("TOKEN"))

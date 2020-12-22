from Dataclasses import SingleGuildData
from typing import Optional
import discord
import yaml
from discord.ext import commands

client = commands.Bot(command_prefix=',', case_insensitive=True)

@client.event
async def on_ready():
    print('bot on')

@client.event
async def on_message(message):
    # canal para o qual vai ser enviado o log da mensagem DM
    el = SingleGuildData.get_instance().channel

    # verifica se a mensagem é na DM e envia um embed para o canal escolhido
    if message.guild is None and not message.author.bot:
        embed = discord.Embed(title="Mensagem enviada para a DM do bot", description= message.content, color=0xff0000)
        embed.set_author(name= message.author.name, icon_url= message.author.avatar_url)
        await el.send(embed=embed)

    await client.process_commands(message)


@client.command()
# envia uma mensagem para a dm da pessoa mencionada, um embed ensinando a responder e deleta a mensagem do comando
async def dm(ctx, user: discord.Member, *, message:str):
    """Envia uma mensagem para a dm da pessoa mencionada.
    é necessário de que a DM dela esteja aberta.
    """
    await user.send(message)
    await user.send(embed=discord.Embed(title="Responda seu amigo (ou inimigo) anônimo!", description="Para responder use `,responder <mensagem>`", color=0xff0000))

    print(message) # cadê a privacidade?????

    await ctx.message.delete()


@client.command()
# estranho
async def uiui(ctx):
   await ctx.channel.send('gozei')

@client.command()
# manda oi pra pessoa
async def oibot(ctx):
   await ctx.channel.send('Oieeeeee {}!'.format(ctx.message.author.name))

@client.command(aliases=["channel", "sc"])
@commands.has_permissions(manage_channels=True)
async def setchannel(ctx, channel: Optional[discord.TextChannel]):

    inst = SingleGuildData.get_instance()
    inst.channel = ctx.channel if channel is None else channel
    await ctx.channel.send('Canal {} adicionado como canal principal de respostas'.format(inst.channel.mention))

with open('credentials.yaml') as t:
    token = yaml.load(t, Loader=yaml.FullLoader)
client.run(token.get("TOKEN"))

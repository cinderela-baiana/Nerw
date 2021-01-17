from discord.ext import commands, tasks
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.conversation import Statement

import discord
import asyncio
import random

class Fun(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def chatbot(ctx, *, texto: str):
        async with ctx.channel.typing():
            resposta = self.client.chatter_thread.generate_response(pergunta)

            await ctx.channel.send(f"{ctx.author.mention} " + str(resposta))
            self.client.last_statements[ctx.author.id] = texto

    @commands.command(name="banrandom", aliases=["banc"])
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def randomban(self, ctx):
        """Bane alguém aleatóriamente"""

        client = self.client

        msg = await ctx.send("Fique atento de que o bot vai **realmente banir alguém**...\nPronto?")
        await msg.add_reaction("👎")
        await msg.add_reaction("👍")

        try:
            def react(reaction, user):
                return reaction.emoji in ["👍", "👎"] and user.id == ctx.author.id and reaction.message.id == msg.id
            reaction, user = await client.wait_for("reaction_add", check=react, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("comando cancelado.")
        else:
            if reaction.emoji == "👎":
                await ctx.send("comando cancelado.")
                return
            invite = random.choice(await ctx.guild.invites())

            memb = random.choice(list(filter(lambda member : member.top_role < ctx.me.top_role, ctx.guild.members)))
            await ctx.send(f"Eu escolhi {memb} pra ser banido :smiling_imp:...")

            await memb.send(f"Oi, você foi banido do `{ctx.guild.name}`, pelo comando banrandom, "
                        "daqui a 5 segundos, tente entrar no servidor usando esse convite: {invite.url}")

            await memb.ban(reason=f"Banido devido ao comando ,banrandom executado por {ctx.author}")

            await ctx.send(f"{ctx.author.mention} ele foi banido.")

            await asyncio.sleep(5)
            await ctx.guild.unban(memb, reason="Tinha sido banido pelo ,banrandom")

    @commands.command()
    @commands.cooldown(1, 120.0, commands.BucketType.guild)
    async def textão(ctx):
        """Faz um textão do tamanho do pinto do João."""
        with ctx.typing():
            await asyncio.sleep(120)
        await ctx.channel.send("lacrei manas")
        await ctx.message.delete()

class Misc(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    # manda oi pra pessoa
    async def oibot(ctx):
        """Tá carente? Usa esse comando!"""
        await ctx.channel.send('Oieeeeee {}!'.format(ctx.message.author.name))

    @commands.command()
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

def setup(client):
    client.add_cog(Misc(client))
    client.add_cog(Fun(client))

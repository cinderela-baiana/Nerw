from discord.ext import commands, tasks, menus
from PIL import Image, ImageDraw
from geopy.geocoders import Nominatim
from typing import *
from chatter_thread import ChatterThread

import discord
import asyncio
import random
import io
import datetime
import aiohttp
apitempo = '462cc03a77176b0e983f9f0c4c192f3b'
tempourl = "https://api.openweathermap.org/data/2.5/onecall?"
geolocator = Nominatim(user_agent='joaovictor.lg020@gmail.com')

class Tempo(menus.Menu):
    def __init__(self, ctx, request, cidade):
        super().__init__()
        self.cidade = cidade
        self.page = 0
        self.ctx = ctx
        self.request = request

    async def get_weather(self, page):
        ctx = self.ctx

        if self.request.status == 404:
            return

        json = await self.request.json()

        current = json["current"]
        daily = json['daily'][page]
        dt = datetime.datetime.utcnow()
        dt1 = datetime.datetime(dt.year, dt.month, dt.day, 1)
        dt1 = dt1 + datetime.timedelta(days=page)
        dt1 = int(dt1.timestamp())

        dt2 = datetime.datetime(dt.year, dt.month, dt.day, 23)
        dt2 = dt2 + datetime.timedelta(days=page)
        dt2 = int(dt2.timestamp())

        period = daily

        pop = daily["pop"]

        current_temperature = period['temp']
        current_temperature_day = current_temperature.get('day')

        current_temperature_celsiuis = str(round(current_temperature_day - 273.15))
        current_humidity = period['humidity']
        current_weather = period["weather"]
        weather_description = current_weather[0]['description']

        alerts = daily.get('alerts')

        if alerts is not None:
            alerts = alerts[0]['description']
        else:
            alerts = 'Nenhum'

        icon = current_weather[0]['icon']
        iconurl = f'http://openweathermap.org/img/wn/{icon}@2x.png'
        dtnow = datetime.datetime.now() + datetime.timedelta(days=page)

        dt = datetime.datetime.utcnow()
        ctx = self.ctx

        embed = discord.Embed(title=f"Tempo em {self.cidade} {dtnow.day}/{dtnow.month}/{dtnow.year}",
                              color=ctx.guild.me.top_role.color,
                              timestamp=ctx.message.created_at)

        embed.add_field(name="Descrição", value=f"**{weather_description.title()}**", inline=False)
        embed.add_field(name="🌡️ Temperatura (ºC)", value=f"Média: **{current_temperature_celsiuis}°C**",
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

class Fun(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.last_statements = {}

    @commands.command()
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def chatbot(self, ctx, *, texto: str):
        """'Conversa' com o chatbot.

        Uma resposta pode demorar de 5 a 15 segundos."""

        async with ctx.channel.typing():
            chat = self.client.chat_thread
            
            if not hasattr(self.client, "chat_thread") or not chat.available:
                await ctx.reply("O comando `chatbot` não pôde ser executado por que"
                                    " o chatter está indisponível.")
                return

            resposta = chat.generate_response(texto)
        await ctx.reply(resposta.text)
        self.last_statements[ctx.author.id] = texto

    @commands.command()
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def include(self, ctx, *, texto: str):
        """
        Coloca uma nova possível resposta para a última pergunta
        executada com o `,chatbot`.

        **Nota**: Não é 100% de certeza que da próxima vez que você
        invocar o comando novamente, você irá receber a resposta inserida, e o bot
        também aprende essa resposta para aplicar em outras perguntas.
        """
        try:
            stat = self.last_statements[ctx.author.id]
        except KeyError:
            await ctx.reply("Você não usou o `,chatbot`.")
            return

        async with ctx.channel.typing():
            chat: ChatterThread = self.client.chat_thread

            if not hasattr(self.client, "chat_thread") or not chat.available:
                await ctx.reply("O comando `include` não pôde ser executado por que"
                                " o chatter está indisponível.")
                return
            chat.learn_response(texto, self.last_statements[ctx.author.id])
            await ctx.reply("Sua resposta foi gravada.")

    @commands.command(name="banrandom", aliases=["banr"])
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
            return
        else:
            if reaction.emoji == "👎":
                await ctx.send("comando cancelado.")
                return
            invite = random.choice(await ctx.guild.invites())

            # só pegar membros que tem cargo menor que o do bot (para evitar erros)
            memb = random.choice(list(filter(lambda member : member.top_role < ctx.me.top_role, ctx.guild.members)))
            await ctx.send(f"Eu escolhi {memb} pra ser banido :smiling_imp:...")

            await memb.send(f"Oi, você foi banido do `{ctx.guild.name}`, pelo comando banrandom, "
                        "daqui a 5 segundos, tente entrar no servidor usando esse convite: {invite.url}")

            await memb.ban(reason=f"Banido devido ao comando ,banrandom executado por {ctx.author}")

            await ctx.send(f"{ctx.author.mention} ele foi banido.")

            await asyncio.sleep(5)
            await ctx.guild.unban(memb, reason="Tinha sido banido pelo ,banrandom")

    def get_colors(self, image, colors=10, resize=150):
        if isinstance(image, bytes):
            image = io.BytesIO(image)
        image = Image.open(image)

        image = image.copy()
        image.thumbnail((resize, resize))

        palt = image.convert("P", palette=Image.ADAPTIVE, colors=colors)
        palette = palt.getpalette()
        color_counts = sorted(palt.getcolors(), reverse=True)
        colors = []

        for c in range(len(colors) + 1):
            palette_index = color_counts[c][1]
            dominant_color = palette[palette_index*3:palette_index*3+3]

            colors.append(tuple(dominant_color))

        return colors

    def save_palette(self, colors, swatchsize=20, outfile="palette.png"):
        num_colors = len(colors)
        palette = Image.new('RGB', (swatchsize*num_colors, swatchsize))
        draw = ImageDraw.Draw(palette)

        posx = 0
        for color in colors:
            draw.rectangle([posx, 0, posx+swatchsize, swatchsize], fill=color) 
            posx = posx + swatchsize

        del draw
        palette.save(outfile, "PNG")

    @commands.command()
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def domin(self, ctx, member: Optional[discord.Member]):
        """
        Pega a cor dominante do seu avatar ou do membro *member*.

        As vezes a cor retornada, pode parecer não ser precisa, mas é basicamente
        a cor com a maior quantidade de pixels coloridos com aquela cor, então
        pode variar com o tamanho da imagem.
        """
        avatar = (member or ctx.author).avatar_url

        colors = self.get_colors(await avatar.read())
        self.save_palette(colors)

        with open("palette.png", "rb") as fp:
            file = discord.File(fp, "palette.png")

        await ctx.reply(file=file)

    @commands.command(name="kickrandom", aliases=["kickr"])
    @commands.has_guild_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    async def kickrandom(self, ctx):
        """Expulsa alguém aleatóriamente."""

        client = self.client

        msg = await ctx.send("Fique atento de que o bot vai **realmente expulsar alguém**...\nPronto?")
        await msg.add_reaction("👎")
        await msg.add_reaction("👍")

        try:
            def react(reaction, user):
                return reaction.emoji in ["👍", "👎"] and user.id == ctx.author.id and reaction.message.id == msg.id
            reaction, user = await client.wait_for("reaction_add", check=react, timeout=30.0)
        except asyncio.TimeoutError:
            return
        else:
            if reaction.emoji == "👎":
                await ctx.send("comando cancelado.")
                return
            invite = random.choice(await ctx.guild.invites())

            memb = random.choice(list(filter(lambda member : member.top_role < ctx.me.top_role, ctx.guild.members)))
            await ctx.send(f"Eu escolhi {memb} pra ser expulso :smiling_imp:...")

            await memb.send(f"Oi, você foi banido do `{ctx.guild.name}`, pelo comando kick, tente entrar no servidor usando esse convite: {invite.url}")
            await memb.kick(reason=f"expulso devido ao comando ,banrandom executado por {ctx.author}")
            await ctx.send(f"{ctx.author.mention} ele foi expulso.")

    @commands.command(aliases=["textao"])
    @commands.cooldown(1, 120.0, commands.BucketType.channel)
    async def textão(self, ctx):
        """Faz um textão do tamanho do pinto do João."""
        with ctx.typing():
            await asyncio.sleep(120)
        await ctx.channel.send("lacrei manas")
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

class Misc(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def oibot(self, ctx):
        """Tá carente? Usa esse comando!"""
        await ctx.channel.send('Oieeeeee {}!'.format(ctx.message.author.name))

    @commands.command()
    @commands.cooldown(1, 10.0, commands.BucketType.member)
    async def enviar(self, ctx, user: Union[discord.Member, discord.User], *, msg: str):
        """Envia uma mensagem para a dm da pessoa mencionada.
        é necessário de que a DM dela esteja aberta."""
        description = """
        Lembre-se de responder a mensagem enviada usando o novo sistema, conforme o
        exemplo abaixo.
        """

        files = [await att.to_file() for att in ctx.message.attachments]
        respmsg = await user.send(msg, files=files)
        embed = discord.Embed(title="Responda seu amigo (ou inimigo) anônimo!",
                        description="Para responder use `,responder <mensagem>`\n" + description,
                        color=self._get_embed_color(ctx))
        embed.set_image(url="https://i.ibb.co/sF6pVsn/enviar-example.png")
        await user.send(embed=embed)

        if ctx.guild is not None:
            # não pode apagar mensagens do destinatário na DM
            await ctx.message.delete()

        def check(message: discord.Message):
            msgcon = message.content.startswith(",responder") and message.reference is not None \
                        and message.reference.message_id == respmsg.id
            return message.author.id == user.id and message.guild is None and msgcon

        guild = self.client.get_guild(790744527450800139)
        channel = guild.get_channel(790744527941009480)

        enviar_embed = discord.Embed(title=",enviar usado.", description=ctx.message.content,
                            color=self._get_embed_color(ctx))
        enviar_embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await channel.send(embed=enviar_embed)

        try:
            message = await self.client.wait_for("message",
                                            check=check,
                                            timeout=300.0)
        except asyncio.TimeoutError:
           return
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

    @commands.cooldown(1, 20.0, commands.BucketType.member)
    @commands.command()
    async def tempo(self, ctx, *, cidade: str):
        """Verifica o tempo atual na sua cidade
           """
        cidade = cidade.title()

        if cidade.startswith('Cidade do'):
            cidade = 'rolândia'

        locator = geolocator.geocode(cidade)
        urlcompleta = tempourl + "lat=" + str(locator.latitude) + "&lon=" + str(locator.longitude) + '&appid=' + apitempo + "&lang=pt_br"

        async with aiohttp.ClientSession() as session:
            #não é possível usar um gerenciador de contexto aqui porque
            #o Tempo (classe) chama funções que só estão disponíveis quando
            #a conexão ainda está aberta.

            request = await session.get(urlcompleta)
            w = Tempo(ctx, request, cidade)

            await w.start(ctx)
            del request

    @commands.command()
    async def invite(self, ctx):
        """
        Recebe um link para convidar o bot para um servidor.
        """
        permissions = discord.Permissions(administrator=True)
        url = discord.utils.oauth_url(self.client.user.id, permissions)
        await ctx.reply(f"Para convidar o bot para o seu servidor, use este link -> <{url}>.")

    def _get_embed_color(self, ctx: commands.Context):
        if isinstance(ctx.me, discord.ClientUser): # estamos em uma DM.
            return discord.Color.dark_red()
        return ctx.me.color

def setup(client):
    client.add_cog(Misc(client))
    client.add_cog(Fun(client))

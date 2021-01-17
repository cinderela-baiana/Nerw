from discord.ext import commands
import chess
import discord
import asyncio
from typing import Optional, Union
import random
import yaml
import logging
from cairosvg import svg2png
import chess.svg
import chess.engine
from discord.ext import menus

logging.basicConfig(level=logging.INFO)

with open('config/credentials.yaml') as t:
    credentials = yaml.load(t)

brd = {}
alias = {}
channels = {}

class Chess(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.engine = chess.engine.SimpleEngine.popen_uci("stockfish.exe")
        logging.info("engine do xadrez carregada!")


    @commands.command(aliases=["xadin"])
    @commands.bot_has_permissions(manage_channels=True)
    async def xadrez_iniciar(self, ctx, userplayer: Union[discord.Member, str]):
        """
        Cria uma partida de xadrez.

        O oponente pode ser o computador ou um membro do servidor.
        """
        client = self.client

        if ctx.author in channels.keys():
            await ctx.reply("Você já está em uma partida.")

        if userplayer != ctx.author: #and userplayer != client.user.id:]
            if userplayer != "computador" and isinstance(userplayer, discord.Member):
                mensagem = await ctx.send(f'Ok, agora aguarde que o usuário {userplayer.mention} reaja à esta mensagem.')
                await mensagem.add_reaction("👍")
                def checkreaction(reaction, user):
                    return user == userplayer and str(reaction.emoji)  == '👍'
                try:
                    reaction, user = await self.client.wait_for("reaction_add",
                                             check=checkreaction,
                                             timeout=120)
                except asyncio.TimeoutError:
                    await ctx.send("Oh não! O usuário não reagiu a tempo.")
                    return

            channel = channels[ctx.author.id] = await self.create_channel(ctx, userplayer)
            mentions = f"{ctx.author.mention} "
            if userplayer != 'computador':
                mentions += " {userplayer.mention} "
            await channel.send(f"{mentions} Que os jogos comecem!")
            rdm = random.randint(1, 2)

            if rdm == 1:
                black = self.client.user.id
                white = ctx.author.id
            else:
                white = self.client.user.id
                black = ctx.author.id

            alias[ctx.author.id] = ctx.me if userplayer == "computador" else userplayer
            alias[ctx.me.id if userplayer == "computador" else userplayer] = ctx.me
            i = userplayer.id if userplayer != "computador" else ctx.me.id
            brd[i] = chess.Board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'), white, black

            color = "branco" if white == ctx.author.id else "preto"

            await channel.send(f"{ctx.author.mention} Você é o **{color}**")

            alias[self.client.user.id] = ctx.author.id
            alias[ctx.author.id] = ctx.author.id
            brd[ctx.author.id] = chess.Board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'), white, black, 'pc'
            await imageboard(ctx, list(brd[ctx.author.id])[0])

            logging.info("Nova partida de xadrez criada.")

    async def create_channel(self, ctx, userplayer):
        """
        Cria o canal do xadrez.
        """

        ov = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            ctx.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        }

        display = "CPU"
        if userplayer is not None and isinstance(userplayer, discord.Member):
            ov[userplayer] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            print(userplayer)
            display = userplayer.display_name

        channel = await ctx.guild.create_text_channel(f"xadrez-{ctx.author.display_name}-{display}",
                    overwrites=ov, topic="cu")
        return channel

    async def imageboard(self, ctx, tab):
        user1 = alias[ctx.author.id]
        user2 = list(brd[alias[ctx.author.id]])[2]
        a = chess.svg.board(board=tab, size=800)
        channel = channels[ctx.author.id]

        svg2png(bytestring=a, write_to='outputboard.png')
        file = discord.File('outputboard.png')

        await channel.send(file=file)

        if tab.is_game_over() == False:
             if tab.turn == chess.WHITE:
                 turn = list(brd[alias[ctx.author.id]])[1]

             elif tab.turn == chess.BLACK:
                 turn = list(brd[alias[ctx.author.id]])[2]

             if tab.is_check():
                await channel.send('Xeque!')

             await channel.send(f'É a vez de <@{turn}>\n Utilize `,xadrez <coordenada inicial> <coordenada final>` para jogar.')

             if turn == self.client.user.id:
                 result = self.engine.play(tab, chess.engine.Limit(time=0.1))
                 tab.push(result.move)
                 brd[ctx.author.id]
                 await imageboard(ctx, tab)
        else:
            await channel.send("Xeque-mate!")
            await end_match(ctx, list(brd[alias[ctx.author.id]])[1], tab)

    async def end_match(self, ctx, winner, *, table=None):
        # lógica compartilhada quando uma partida é encerrada.
        if isinstance(winner, int):
            winner = ctx.guild.get_member(winner)

        try:
            channel = channels[ctx.author.id]
        except KeyError:
            logging.warn("Não foi possível pegar o canal onde a partida aconteceu.")
            return

        if winner is None:
            await channel.send("Não foi possível determinar o ganhador. Então fica considerado como um empate.")
            return

        await channel.send(f"{winner.mention} foi o vencedor. Parabéns!\nhttps://img1.recadosonline.com/713/006.gif")

        await asyncio.sleep(10)
        await channel.delete()

        del brd[ctx.author.id]
        del alias[ctx.author.id]
        del alias[winner.id]
        del channels[ctx.author.id]

    @commands.command()
    async def xadrez(self, ctx, coord1, coord2):
        try:
            brdauth = list(brd[alias[ctx.author.id]])[0]
            if brdauth.turn == chess.WHITE:
                turn = list(brd[alias[ctx.author.id]])[1]
            if brdauth.turn == chess.BLACK:
                turn = list(brd[alias[ctx.author.id]])[2]
            if turn == ctx.author.id:
                Nf3 = chess.Move.from_uci(coord1 + coord2)
                if Nf3 in brdauth.legal_moves:
                    brdauth.push(Nf3)
                    await self.imageboard(ctx, brdauth)
                else:
                    await ctx.reply('Este movimento não é permitido.')
            else: await ctx.reply('Espera sua vez de jogar mano')
        except KeyError:
            await ctx.reply("Você não tem uma partida em andamento. Inicie uma com `,xadrez_iniciar`.")

    @commands.command(aliases=["xadfi"])
    async def xadrez_finalizar(self, ctx):
        try:
            user1 = alias[ctx.author.id]
            user2 = list(brd[alias[ctx.author.id]])[2]
            brdauth = list(brd[alias[ctx.author.id]])[0]

            reply = await ctx.reply("Você dará a vitória para o oponente, deseja mesmo finalizar o jogo?")

            await reply.add_reaction("👍")

            def checkreaction(reaction, user):
                return user == ctx.author and str(reaction.emoji) == '👍' and reaction.message == reply

            try:
                reaction, user = await self.client.wait_for("reaction_add",
                                                       check=checkreaction,
                                                       timeout=120)
            except asyncio.TimeoutError:
                pass
            else:
                    if ctx.author.id == list(brd[alias[ctx.author.id]])[1]:
                        await self.end_match(ctx, list(brd[alias[ctx.author.id]])[2])
                    else:
                        await self.end_match(ctx, list(brd[alias[ctx.author.id]])[1])

        except KeyError:
            await ctx.reply("Você não tem uma partida em andamento. Inicie uma com `,xadin`.")

def setup(client):
    client.add_cog(Chess(client))

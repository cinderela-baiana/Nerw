from discord.ext import commands
import chess
import discord
import asyncio
from typing import Optional, Union
import random
import emoji
import logging
from cairosvg import svg2png
import chess.svg
import chess.engine
import secrets
import os
import warnings
import uuid
import collections

from Utils import DatabaseWrap, Field

logging.basicConfig(level=logging.INFO)

brd = {}
alias = {}
channels = {}

# importante: mudar isso pode quebrar o sistema de rankings do xadrez
CHESS_TABLE_NAME = "chess_matches"
CLEAN_CHESS_TABLE = chess.Board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')

MatchData = collections.namedtuple("MatchData", ("board", "white", "black", "difficulty"))

def _get_executable_suffix():
    import sys

    if sys.platform == "win32":
        return ".exe"
    return ""

class Chess(commands.Cog):

    def __init__(self, client):
        logging.info("Carregando engine do xadrez")
        self.client = client
        file = "config/stockfish" + _get_executable_suffix()
        if not os.path.exists(file):
            file = "stockfish" + _get_executable_suffix()
            warnings.warn("O executável do stockfish deve estar na pasta config.", DeprecationWarning,
                          stacklevel=2)
        self._wins = None
        self.engine = chess.engine.SimpleEngine.popen_uci(file)
        logging.info("engine do xadrez carregada!")

    def _create_table(self):
        """
        Criação da tabela de SQL (para os rankings de xadrez.)
        """
        with DatabaseWrap.from_filepath("main.db") as wrap:
            wrap.create_table_if_absent("chess_matches", [
                Field(name="match", type="TEXT NOT NULL"),
                Field(name="winner", type="TEXT")
            ])

    def _post_winner(self, winner, match_id=None):
        if isinstance(winner, discord.Member):
            winner = winner.id

        if match_id is None:
            match_id = str(uuid.uuid4())

        with DatabaseWrap.from_filepath("main.db") as wrap:
            wrap.database.execute("INSERT INTO chess_matches(match, winner) VALUES(?,?)", (match_id, winner))

    def calculate_positions(self, competitors):
        max_num = 0
        winn = []
        if self._wins is not None:
            return self._wins
        for compt, score in competitors:
            winn.insert(score, (compt, score))
        if self._wins is not None:
            self._wins = list(reversed(winn))
        return list(reversed(winn))

    def _refresh_wins(self):
        """Força que o cálculo das posições seja feito
         na próxima chamada ao calculate_position."""
        self._wins = None

    @commands.command(aliases=["xadr", "xadran"])
    async def xadrez_rank(self, ctx):
        with DatabaseWrap.from_filepath("main.db") as wrap:
            wins = wrap.get_item("chess_matches", item_name="winner", fetchall=True)
        winn = set()


        for win_id in wins:
            if win_id is None:
                continue
            win_id = win_id[0]
            count = wins.count((win_id,))
            winn.add((win_id, count))
        descr = []

        big_chunk = list(enumerate(self.calculate_positions(winn), 1))

        for position, (winner_id, win_count) in big_chunk:
            user = ctx.guild.get_member(int(winner_id))
            if user is None:
                user = winner_id

            # vai aparecer esses emojis da lista para o 1º, 2º e 3º
            # lugar do ranking.
            medals = [emoji.emojize(":trophy:"),
                      emoji.emojize(":second_place:"),
                      emoji.emojize(":third_place:")]
            if position in [1, 2, 3]:
                position = medals[position - 1]
            else:
                position = str(position) + "º"

            descr.append(f"{position} {user} - {win_count}")

        await ctx.reply("\n".join(descr))

    @commands.command(aliases=["xadin"])
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def xadrez_iniciar(self, ctx, userplayer: Union[discord.Member, str]):
        """
        Cria uma partida de xadrez.
        O oponente pode ser o computador ou um membro do servidor.

        O motor utilizado para as jogadas do computador é o Stockfish.
        """
        client = self.client
        self._create_table()

        if ctx.author.id not in alias.keys() and ctx.author.id not in alias.values():
            if userplayer != ctx.author: #and userplayer != client.user.id:
                if userplayer != "computador" and isinstance(userplayer, discord.Member):
                    mensagem = await ctx.send(f'Ok, agora aguarde que o usuário {userplayer.mention} reaja à esta mensagem.')
                    await mensagem.add_reaction("👍")
                    def checkreaction(reaction, user):
                        return user == userplayer and str(reaction.emoji)  == '👍' and reaction.message == mensagem
                    try:
                        reaction, user = await client.wait_for("reaction_add",
                                                               check=checkreaction,
                                                               timeout=120)

                    except asyncio.TimeoutError:
                        await ctx.send("Oh não! O usuário não reagiu a tempo.")
                        return
                    else:
                        pass

                mentions = f"{ctx.author.mention}"
                dificuldade = 0
                if userplayer != 'computador':
                    print(type(userplayer), userplayer)
                    mentions += f" {userplayer.mention} "

                else:
                    userplayer = ctx.me
                    difficultylist = {"facinho" : 0, "fácil" : 5, "médio" : 10, "difícil" : 15, "hardicori" : 20}
                    await ctx.send("Qual dificuldade você deseja:\n Facinho, fácil, médio, difícil ou hardicori?")

                    def check(message):
                        msgcon = message.content.lower() in difficultylist.keys()
                        return message.author.id == ctx.author.id and message.channel == ctx.channel and msgcon

                    try:
                        message = await client.wait_for("message",
                                                        check=check,
                                                        timeout=30.0)
                    except asyncio.TimeoutError:
                        return
                    else:
                        content = message.content.lower()
                        dificuldade = difficultylist[content]

                data = self._create_match_id(ctx.author, userplayer)
                channel = channels[userplayer.id] = await self.create_channel(ctx, userplayer, match_id=data)
                await channel.send(f"{mentions} Que os jogos comecem!")
                rdm = random.randint(1, 2)

                if rdm == 1:
                    black = userplayer.id
                    white = ctx.author.id
                else:
                    white = userplayer.id
                    black = ctx.author.id

                alias[ctx.author.id] = userplayer.id
                alias[userplayer.id] = userplayer.id
                brd[userplayer.id] = MatchData(board=CLEAN_CHESS_TABLE, white=white, black=black, difficulty=dificuldade)

                color = "branco" if white == ctx.author.id else "preto"

                await channel.send(f"{ctx.author.mention} Você é o {color}")
                await self.imageboard(ctx, brd[alias[ctx.author.id]].board, match_id=data)

                logging.info("Nova partida de xadrez criada.")
        else:
            await ctx.reply('Você já tem uma partida em andamento.')

    async def create_channel(self, ctx, userplayer, *, match_id=None):
        """
        Cria o canal de xadrez.
        """
        # cria o canal do xadrez.
        ov = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            ctx.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        }

        display = "CPU"
        if match_id is None:
            match_id = self._create_match_id(ctx.author, userplayer)
        if userplayer is not None and isinstance(userplayer, discord.Member):
            ov[userplayer] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            display = userplayer.display_name
        category = discord.utils.get(ctx.guild.channels, name='Xadrez')
        if category is None:
            category = await ctx.guild.create_category_channel('Xadrez')
        channel = await ctx.guild.create_text_channel(f"xadrez-{ctx.author.display_name}-{display}",
                                                      overwrites=ov, topic=f"ID -> {match_id}", category= category)
        return channel

    def _create_match_id(self, *competitors) -> str:
        data = secrets.token_urlsafe(16)
        return data

    async def imageboard(self, ctx, tab, move=None, match_id=None):
        square = None
        if tab.is_check():
            pieces = tab.pieces(piece_type=chess.KING, color=tab.turn)
            for piece in pieces:
                square = piece
        a = chess.svg.board(board=tab, size=800, lastmove=move, check=square)
        channel = channels[alias[ctx.author.id]]

        svg2png(bytestring=a, write_to='outputboard.png')
        file = discord.File('outputboard.png')

        embed = discord.Embed(color=ctx.guild.me.color)

        embed.set_image(url="attachment://outputboard.png")
        embed.set_footer(text="Utilize ,xadrez <coordenada inicial> <coordenada final> para jogar."
                              "\nUtilize `,xadfi` para desistir.")

        await channel.send(file=file, embed=embed)
        if not tab.is_game_over():
            turn = self.turn(ctx)
            if tab.is_check():
                await channel.send('https://cdn.discordapp.com/attachments/597071381586378752/796947748401446952/ezgif-2-9143b9b40c89.gif')
            turn = ctx.guild.get_member(turn)
            await channel.send(f'É a vez de {turn.mention}')
            if turn == ctx.me:
                async with channel.typing():
                    while True:
                        try:
                            diff = brd[alias[ctx.author.id]].difficulty
                            result = self.engine.play(tab, chess.engine.Limit(time=5), options={'Skill Level': diff})
                            tab.push(result.move)
                            await self.imageboard(ctx, tab, result.move)
                            break
                        except:
                            continue
        else:
            if tab.is_checkmate():
                await channel.send("Xeque-mate!")
            elif tab.is_stalemate():
                await ctx.send("Rei afogado!")
            elif tab.is_insufficient_material():
                await ctx.send("Material insuficiente!")
            if tab.result() == '1-0':
                white = brd[alias[ctx.author.id]].white
                await ctx.send(embed=discord.Embed(title=f"Partida finalizada", description= f'<@{white}> foi o vencedor. Parabéns!').set_image(url='https://img1.recadosonline.com/713/006.gif'))
            elif tab.result() == '0-1':
                black = brd[alias[ctx.author.id]].black
                await ctx.send(embed=discord.Embed(title=f"Partida finalizada", description= f'<@{black}> foi o vencedor. Parabéns!').set_image(url='https://img1.recadosonline.com/713/006.gif'))
            elif tab.result() == '1/2-1/2':
                await ctx.send(embed=discord.Embed(title= 'Temos um empate!', description= 'GG, peguem seus troféus de empate'))
            await self.end_match(ctx, match_id)

    async def end_match(self, ctx, winner=None, *, match_id=None):
        # lógica compartilhada quando uma partida é encerrada.

        try:
            channel = channels[alias[ctx.author.id]]
        except KeyError:
            logging.warning("Não foi possível pegar o canal onde a partida aconteceu.")
            return
        if winner != None:
            if isinstance(winner, int):
                winner = ctx.guild.get_member(winner)
            elif isinstance(winner, str):
                try:
                    winner = int(winner)
                except ValueError:
                    winner = ctx.guild.get_member_named(winner)
                else:
                    winner = ctx.guild.get_member()
            embed = discord.Embed(title=f"Partida finalizada",
                                                    description= f'{winner.mention} foi o vencedor. Parabéns!')
            embed.set_image(url='https://img1.recadosonline.com/713/006.gif')
            await channel.send(embed=embed)

            self._post_winner(winner, match_id)
        self._refresh_wins()
        await asyncio.sleep(45)
        await channel.delete()


        user1 = brd[alias[ctx.author.id]].white
        user2 = brd[alias[ctx.author.id]].black
        del brd[alias[ctx.author.id]]
        del alias[user1]
        del alias[user2]
        del channels[alias[ctx.author.id]]

    def turn(self, ctx):
        brdauth = brd[alias[ctx.author.id]].board
        if brdauth.turn == chess.WHITE:
            turn = brd[alias[ctx.author.id]].black
        if brdauth.turn == chess.BLACK:
            turn = brd[alias[ctx.author.id]].white
        return turn

    @commands.command(aliases=["xad"])
    async def xadrez(self, ctx, coord1, coord2):
        """
        Realiza uma jogada de xadrez.
        Obviamente você precisa estar em uma partida de xadrez para utilizar esse comando.

        **Argumentos:**
            \* coord1: a primeira coordenada, é usada para escolher a peça desejada.
            \* coord2: a segunda coordenada, é o destino da peça localizada em *coord1*.

        **Exemplo:**
            \* Mover um peão 2 casas pra frente:
                `,xadrez a2 a4`
        """
        turn = self.turn(ctx)
        brdauth = brd[alias[ctx.author.id]].board
        try:
            if turn == ctx.author.id:
                Nf3 = chess.Move.from_uci(coord1 + coord2)
                if Nf3 in brdauth.legal_moves:
                    brdauth.push(Nf3)
                    await self.imageboard(ctx=ctx, tab=brdauth, move=Nf3)
                else:
                    await ctx.reply('Este movimento não é permitido.')
            else:
                await ctx.reply('Espera sua vez de jogar mano')
        except KeyError:
            await ctx.reply("Você não tem uma partida em andamento. Inicie uma com `,xadrez_iniciar`.")

    @commands.command(aliases=["xadfi"])
    async def xadrez_finalizar(self, ctx):
        try:
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
                if ctx.author.id == brd[alias[ctx.author.id]].white:
                    await self.end_match(ctx, brd[alias[ctx.author.id]].black)
                else:
                    await self.end_match(ctx, brd[alias[ctx.author.id]].white)

        except KeyError:
            # por algum motivo esse pedaço de código é executado
            # quando o canal é deletado no end_match e por causa disso o discord.py joga um
            # NotFound.
            try:
                await ctx.reply("Você não tem uma partida em andamento. Inicie uma com `,xadin`.")
            except discord.NotFound:
                return

def setup(client):
    client.add_cog(Chess(client))

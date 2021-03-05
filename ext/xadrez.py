from discord.ext import commands
import chess
import discord
import asyncio
from typing import *
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
import sys
import collections

from Utils import DatabaseWrap, Field

logger = logging.getLogger(__name__)

brd = {}
alias = {}
channels = {}

# importante: mudar isso pode quebrar o sistema de rankings do xadrez
CHESS_TABLE_NAME = "chess_matches"

_Py_BaseMatchData = collections.namedtuple("MatchData",
                                           ("board", "white", "black",
                                            "difficulty", "match_id",
                                            "overwrites", "spectators", "creator"))

QUESTION_EMOJI = "<:question:816429295005073419>"
EXCLAMATION_EMOJI = "<:exclamation:816429295102328903> "
CROSS_EMOJI = "<:cross:816429294501756928>"
INFO_EMOJI = "<:4497_info:816429294774517810>"

ONE_EMOJI = "<:1n:816740502342598676>"
TWO_EMOJI = "<:2n:816740535905550366>"
THREE_EMOJI = "<:3n:816740576292503582>"
FOUR_EMOJI = "<:4n:816740620961579048>"
FIVE_EMOJI = "<:5n:816740650002546729>"

class MatchData(_Py_BaseMatchData):
    overwrites: dict
    board: chess.Board
    white: int
    black: int
    spectators: Set[int]
    match_id: str
    creator: int

    def update_overwrites(self, **new_ovs):
        self.overwrites.update(**new_ovs)
        return self.overwrites

    def set_overwrites(self, new_overwrite: dict):
        self._replace(overwrites=new_overwrite)

    def add_spectator(self, spectator):
        if isinstance(spectator, discord.Member):
            spectator = spectator.id
        self.spectators.add(spectator)

    @property
    def channel(self) -> discord.TextChannel:
        chan = channels[self.creator]
        return chan

    @channel.setter
    def chanset(self, _):
        raise AttributeError("channel is read-only")

    async def remove_spectator(self, spectator):
        if spectator in self.overwrites.keys():
            self.overwrites.pop(spectator)
        await self.channel.edit(overwrites=self.overwrites)

        if isinstance(spectator, discord.Member):
            spectator = spectator.id
        self.spectators.remove(spectator)

    async def remove_spectators(self, *spectators):
        for spectator in spectators:
            if spectator in self.overwrites.keys():
                self.overwrites.pop(spectator)
            try:
                self.spectators.remove(spectator)
            except KeyError:
                continue

        await self.channel.edit(overwrites=self.overwrites)

    def __contains__(self, item):
        return

    def __repr__(self):
        return f"MatchData(board={self.board})"

def _get_executable_suffix():
    import sys

    if sys.platform == "win32":
        return ".exe"
    return ""

class Chess(commands.Cog):

    def __init__(self, client):
        logger.info("Carregando engine do xadrez")
        self.client = client
        file = "config/stockfish" + _get_executable_suffix()
        if not os.path.exists(file):
            file = "stockfish" + _get_executable_suffix()
            warnings.warn("O executável do stockfish deve estar na pasta config.", DeprecationWarning,
                          stacklevel=2)
        self._wins = None
        self.engine = chess.engine.SimpleEngine.popen_uci(file)
        logger.info("engine do xadrez carregada!")

    def cog_unload(self):
        self.engine.close()

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

    def get_current_matches(self) -> List[MatchData]:
        """
        Retorna todas as partidas ocorrendo neste momento.
        """
        return list(brd.values())

    def get_current_matches_ids(self) -> List[str]:
        """
        Pega todos os IDs das partidas ocorrendo neste momento, equivale a um `map` no
        get_current_matches(), pegando todos os IDs dele.
        """
        return list(map(lambda match_data : match_data.match_id, self.get_current_matches()))

    def get_match_by_enemy(self, enemy: Union[int, discord.Member]) -> Optional[MatchData]:
        if isinstance(enemy, discord.Member):
            enemy = enemy.id
        return brd.get(enemy)

    def get_match_by_creator(self, creator: Union[int, discord.Member]) -> Optional[MatchData]:
        if isinstance(creator, discord.Member):
            creator = creator.id
        enem = alias.get(creator)
        return self.get_match_by_enemy(enem)

    def get_match_by_id(self, match_id : str) -> Optional[MatchData]:
        for match_data in self.get_current_matches():
            if match_data.match_id == match_id:
                return match_data
        else:
            return

    @commands.group(aliases=["xadspec", "xadrez_spectate"], enabled=True)
    async def xadrez_espectar(self, ctx):
        """
        Grupo de comandos que cuida da parte de espectação de partidas

        Caso nenhum subcomando seja chamado, você precisa fornecer a ID
        da partida.

        Exemplo:
            \* **Entrar em uma partida**

                `,xadspec Uy_su72-wed44`.
        """
        if ctx.invoked_subcommand is None:
            command = self.client.get_command("help")
            await ctx.invoke(command, cmd="xadspec")

    @xadrez_espectar.command(name="join")
    async def xadspec_join(self, ctx, match_code : str):
        """Começa a espectar uma partida de xadrez."""
        match_data = self.get_match_by_id(match_code)

        if match_data is None:
            return await ctx.reply(f"{CROSS_EMOJI} Essa partida não existe ou já terminou.")
        if ctx.author.id in match_data.spectators:
            return await ctx.reply(f"{CROSS_EMOJI} Você já está espectando essa partida.")

        # legal é que não estamos fazendo nenhuma verificação
        # pra caso um dos jogadores saia do servidor.
        channel = match_data.channel
        black, white = ctx.guild.get_member(match_data.black), ctx.guild.get_member(match_data.white)

        ov = {
            ctx.author: discord.PermissionOverwrite(add_reactions=True, read_messages=True, send_messages=False),
        }

        if sys.version_info >= (3,9):
            ov |= match_data.overwrites
        else:
            ov.update(match_data.overwrites)

        if black is not None:
            ov[black] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if white is not None:
            ov[white] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        match_data.set_overwrites(ov)
        await channel.edit(overwrites=ov)
        match_data.add_spectator(ctx.author)
        await ctx.reply(f"O chat de xadrez é o {channel.mention}")

    @xadrez_espectar.command(name="list")
    async def xadspec_list(self, ctx):
        """
        Lista todas as partidas de xadrez disponíveis para serem espectadas.
        """
        scheme = []
        for match in self.get_current_matches():
            blackuser = ctx.guild.get_member(match.black)
            whiteuser = ctx.guild.get_member(match.white)
            scheme.append(f"{match.match_id} - {blackuser} vs. {whiteuser}")
        if scheme == []:
            scheme.append(f"{EXCLAMATION_EMOJI} Nenhuma partida...")

        await ctx.reply(embed=discord.Embed(title="Partidas disponíveis",
                                            description="\n".join(scheme),
                                            color=discord.Color.orange()))

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
                        return
                    else:
                        pass

                mentions = f"{ctx.author.mention}"
                dificuldade = 0
                if userplayer != 'computador':
                    mentions += f" {userplayer.mention} "

                else:
                    userplayer = ctx.me
                    descpr = f"{ONE_EMOJI} - Facinho\n{TWO_EMOJI} - Fácil\n{THREE_EMOJI} - médio\n{FOUR_EMOJI} - difícil \n{FIVE_EMOJI} - hardicori"
                    embed = discord.Embed(title=f"{QUESTION_EMOJI} Escolha a dificuldade", description=descpr, color=discord.Color.from_rgb(240,240,240))
                    reamsg = await ctx.send(embed=embed)

                    emjtup = (ONE_EMOJI, TWO_EMOJI, THREE_EMOJI, FOUR_EMOJI, FIVE_EMOJI)
                    for emj in emjtup:
                        await reamsg.add_reaction(emj)

                    def check(reaction: discord.Reaction, user: discord.Member):

                        return user.id == ctx.author.id and str(reaction.emoji) in emjtup

                    try:
                        reaction, user = await client.wait_for("reaction_add",
                                                        check=check,
                                                        timeout=30.0)
                    except asyncio.TimeoutError:
                        return
                    else:
                        mapping = {
                            ONE_EMOJI: 0, # fácinho
                            TWO_EMOJI: 5, # fácil
                            THREE_EMOJI: 10, # médio
                            FOUR_EMOJI: 15, # difícil
                            FIVE_EMOJI: 20 # hardicori
                        }
                        dificuldade = mapping[str(reaction.emoji)]

                data = self._create_match_id(ctx.author, userplayer)
                rdm = random.randint(1, 2)

                if rdm == 1:
                    black = userplayer.id
                    white = ctx.author.id
                else:
                    white = userplayer.id
                    black = ctx.author.id

                alias[ctx.author.id] = ctx.author.id # compatibilidade
                alias[userplayer.id] = userplayer.id
                cct = chess.Board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
                brd[ctx.author.id] = MatchData(board=cct, white=white,
                                               black=black, difficulty=dificuldade,
                                               match_id=data, overwrites=None, spectators=set(),
                                               creator=ctx.author.id)

                channel = await self.create_channel(ctx, userplayer, match_id=data)
                board : chess.Board = brd[ctx.author.id].board

                if board.turn == chess.WHITE:
                    color = "branco"
                elif board.turn == chess.BLACK:
                    color = "preto"

                await channel.send(f"{mentions} Que os jogos comecem!")
                await channel.send(f"Você ({ctx.author}) é o {color}")
                await self.imageboard(ctx, brd[alias[ctx.author.id]].board)

                logger.info("Nova partida de xadrez criada. (ID -> %s)", data)
        else:
            await ctx.reply(f'{CROSS_EMOJI} Você já tem uma partida em andamento.')

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
                                                      overwrites=ov, topic=f"ID -> {match_id}", category=category)
        channels[alias[ctx.author.id]] = channel
        match = self.get_match_by_id(match_id)
        brd[alias[ctx.author.id]] = match._replace(overwrites=ov)
        return channel

    def _create_match_id(self, *competitors) -> str:
        data = secrets.token_urlsafe(16)
        return data

    async def imageboard(self, ctx, tab, move=None):
        brdobj = brd[alias[ctx.author.id]]
        match_id = brdobj.match_id
        logger.debug("Board Atual -> %s ", brd)
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
                    for _ in range(0, 15):
                        try:
                            diff = brd[alias[ctx.author.id]].difficulty
                            result = self.engine.play(tab, chess.engine.Limit(time=3), options={'Skill Level': diff})
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
                embed = discord.Embed(title=f"Partida finalizada",
                              description=f'<@{white}> foi o vencedor. Parabéns!')
                embed.set_image(url='https://img1.recadosonline.com/713/006.gif')
            elif tab.result() == '0-1':
                black = brd[alias[ctx.author.id]].black
                embed = discord.Embed(title=f"Partida finalizada",
                                      description= f'<@{black}> foi o vencedor. Parabéns!')
                embed.set_image(url='https://img1.recadosonline.com/713/006.gif')
            elif tab.result() == '1/2-1/2':
                embed = discord.Embed(title= 'Temos um empate!',
                                    description= 'GG, peguem seus troféus de empate')
            await channel.send(embed=embed)
            await self.end_match(ctx)

    async def end_match(self, ctx, winner=None):
        # lógica compartilhada quando uma partida é encerrada.

        brdobj = self.get_match_by_creator(ctx.author.id)

        try:
            channel = channels[alias[ctx.author.id]]
        except KeyError:
            logger.warning("Não foi possível pegar o canal onde a partida %s aconteceu.", brdobj.match_id)
            return
        if winner is not None:
            if isinstance(winner, int):
                winner = ctx.guild.get_member(winner)
            elif isinstance(winner, str):
                try:
                    winner = int(winner)
                except ValueError:
                    winner = ctx.guild.get_member_named(winner)
                else:
                    winner = ctx.guild.get_member(winner)

            embed = discord.Embed(title=f"Partida finalizada",
                                                    description= f'{winner.mention} foi o vencedor. Parabéns!')
            embed.set_image(url='https://img1.recadosonline.com/713/006.gif')
            await channel.send(embed=embed)
            logger.info("Partida %s finalizada. (Vencedor: %s)", brdobj.match_id, str(winner))
            self._post_winner(winner, brdobj.match_id)

        user1 = brd[alias[ctx.author.id]].white
        user2 = brd[alias[ctx.author.id]].black
        del brd[alias[ctx.author.id]]
        del alias[user1]
        del alias[user2]
        del channels[alias[ctx.author.id]]

        self._refresh_wins()
        await brdobj.remove_spectators(*brdobj.spectators)
        await asyncio.sleep(45)
        await channel.delete()

    def turn(self, ctx):
        brdauth = brd[alias[ctx.author.id]].board
        if brdauth.turn == chess.WHITE:
            turn = brd[alias[ctx.author.id]].black
        if brdauth.turn == chess.BLACK:
            turn = brd[alias[ctx.author.id]].white
        return turn

    @commands.command(aliases=["xad"])
    @commands.guild_only()
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
        try:
            turn = self.turn(ctx)
        except KeyError:
            return await ctx.reply("Você não está em uma partida de xadrez.")

        board = self.get_match_by_creator(ctx.author)
        brdauth = board.board
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

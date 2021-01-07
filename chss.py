from discord.ext import commands
import chess
import discord
import asyncio
from typing import Optional
import random
import yaml
from cairosvg import svg2png
import chess.svg
import chess.engine

engine = chess.engine.SimpleEngine.popen_uci("C:/Users/joao_2/Downloads/stockfish/stockfish_20090216_x64_ssse.exe")
#motor do xadrez

with open('credentials.yaml') as t:
    credentials = yaml.load(t)
brd = {}
alias = {}
client = commands.Bot(command_prefix=credentials.get("PREFIXO"), case_insensitive=True)

@client.event
async def on_ready():
     print(f'Bot pronto')

@client.command()
async def xadrez_iniciar(ctx, user: discord.User=None):
    if user == None:
        if ctx.author.id not in alias and user not in alias:
            await ctx.reply(embed= discord.Embed(title="Com quem você deseja jogar? ",
                                                 description="Digite um usuário ou `computador` para jogar com a máquina."))
            def check(message):
                return message.author.id == ctx.author.id and message.channel == ctx.channel
            try:
                message = await client.wait_for("message",
                                                check=check,
                                                timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("Oh não! Você demorou muito para responder. :pensive:")
                pass
            else:
                if message.content != "computador":
                    await xadrez_iniciar(ctx, message.content)
                else:
                    await ctx.send("Que os jogos começem!")
                    rdm = random.randint(1, 2)
                    if rdm == 1:
                        black = client.user.id
                        white = ctx.author.id
                    else:
                        white = client.user.id
                        black = ctx.author.id
                    alias[client.user.id] = ctx.author.id
                    alias[ctx.author.id] = ctx.author.id
                    brd[ctx.author.id] = chess.Board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'), white, black, 'pc'
                    print(brd[ctx.author.id])
                    await imageboard(ctx, list(brd[ctx.author.id])[0])
        else:
            await ctx.reply('Você já tem uma partida em andamento.')
    else:
        if user != discord.Member or user != discord.User:
            user = user.replace("<@","")
            user = user.replace('>', '')
            try:
                userplayer = await client.fetch_user(user)
                if userplayer != ctx.author: #and userplayer != client.user.id:
                     mensagem = await ctx.send(f'Ok, agora aguarde que o usuário @{userplayer} reaja à esta mensagem.')
                     mensagem
                     await mensagem.add_reaction("👍")
                     def checkreaction(reaction, user):
                         return user == userplayer and str(reaction.emoji)  == '👍'
                     try:
                         reaction, user = await client.wait_for("reaction_add",
                                                     check=checkreaction,
                                                     timeout=120)
                     except asyncio.TimeoutError:
                         await ctx.send("Oh não! O usuário não reagiu a tempo.")
                     else:
                        await ctx.send("Que os jogos começem!")
                        rdm = random.randint(1,2)
                        print(rdm)
                        if rdm == 1:
                            white = ctx.author.id
                            black = userplayer.id
                        else:
                            white = userplayer.id
                            black = ctx.author.id
                        alias[ctx.author.id] = userplayer.id
                        alias[userplayer.id] = userplayer.id
                        brd[userplayer.id] = chess.Board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'), white, black
                        print(brd)
                        print(list(brd[userplayer.id])[0])
                        await imageboard(ctx, list(brd[userplayer.id])[0])
            except discord.HTTPException:
                await ctx.send('Usuário inválido.')


async def imageboard(ctx, tab):
    user1 = alias[ctx.author.id]
    user2 = list(brd[alias[ctx.author.id]])[2]
    a = chess.svg.board(board=tab, size=800)
    svg2png(bytestring=a, write_to='outputboard.png')
    file = discord.File('outputboard.png')
    await ctx.reply(file=file)
    if tab.is_game_over() == False:
         if tab.turn == chess.WHITE:
             turn = list(brd[alias[ctx.author.id]])[1]
             print('oi')
         if tab.turn == chess.BLACK:
             turn = list(brd[alias[ctx.author.id]])[2]
         if tab.is_check():
             await ctx.send('Xeque!')
         print(tab.is_game_over())
         await ctx.send(f'É a vez de <@{turn}>\n Utilize `,xadrez <coordenada inicial> <coordenada final>` para jogar.')
         if turn == client.user.id:
             result = engine.play(tab, chess.engine.Limit(time=0.1))
             tab.push(result.move)
             brd[ctx.author.id]
             await imageboard(ctx, tab)
    else:
        await ctx.send("Xeque-mate!")
        if tab.result == '1-0':
            await ctx.send(f"<@{list(brd[alias[ctx.author.id]])[1]}> foi o vencedor. Parabéns!\nhttps://img1.recadosonline.com/713/006.gif")
        else:
            await ctx.send(f"<@{list(brd[alias[ctx.author.id]])[1]}> foi o vencedor. Parabéns!\nhttps://img1.recadosonline.com/713/006.gif")
        await ctx.send(tab.result())
        del brd[user1]
        del alias[user1]
        del alias[user2]


@client.command(pass_context=True)
async def xadrez(ctx, coord1, coord2):
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
                await imageboard(ctx, brdauth)
            else:
                await ctx.reply('Este movimento não é permitido.')
        else: await ctx.reply('Espera sua vez de jogar mano')
    except KeyError:
        await ctx.reply("Você não tem uma partida em andamento. Inicie uma com `,xadrez_iniciar`.")

@client.command()
async def xadrez_finalizar(ctx):
    try:
        user1 = alias[ctx.author.id]
        user2 = list(brd[alias[ctx.author.id]])[2]
        brdauth = list(brd[alias[ctx.author.id]])[0]
        reply = await ctx.reply("Você dará a vitória para o oponente, deseja mesmo finalizar o jogo?")
        reply
        await reply.add_reaction("👍")

        def checkreaction(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '👍'

        try:
            reaction, user = await client.wait_for("reaction_add",
                                                   check=checkreaction,
                                                   timeout=120)
        except asyncio.TimeoutError:
            pass
        else:
            if ctx.author.id == list(brd[alias[ctx.author.id]])[1]:
                await ctx.send(f"<@{list(brd[alias[ctx.author.id]])[2]}> foi o vencedor. Parabéns!\nhttps://img1.recadosonline.com/713/006.gif")
            else: await ctx.send(f"<@{list(brd[alias[ctx.author.id]])[1]}> foi o vencedor. Parabéns!\nhttps://img1.recadosonline.com/713/006.gif")
            del brd[user1]
            del alias[user1]
            del alias[user2]
    except KeyError:
        await ctx.reply("Você não tem uma partida em andamento. Inicie uma com `,xadrez_iniciar`.")

client.run(credentials.get("TOKEN"))
from chatterbot import ChatBot
import discord
import yaml
from discord.ext import commands
from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.conversation import Statement

with open('config/credentials.yaml') as t:
    credentials = yaml.load(t)

client = commands.Bot(command_prefix=credentials.get("PREFIXO"), case_insensitive=True)

@client.event
async def on_ready():
     print(f'Bot pronto')

@client.command()
async def include(ctx, *, texto: str):
    try:
        question = Statement(text=client.last_statements[ctx.author.id])
    except KeyError:
        return await ctx.send("Você não enviou nenhuma pergunta.")

    client.chatbot.learn_response(Statement(text=texto), question)
    await ctx.send("Pronto! A resposta correta foi registrada.")

client.run(credentials.get("TOKEN"))

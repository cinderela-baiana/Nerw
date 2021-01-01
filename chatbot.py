from chatterbot.trainers import ListTrainer
from chatterbot import ChatBot
import spacy
import discord
import yaml
from discord.ext import commands
from chatterbot.trainers import ChatterBotCorpusTrainer

import en_core_web_sm
nlp = spacy.load("en")

with open('credentials.yaml') as t:
    credentials = yaml.load(t)

client = commands.Bot(command_prefix=credentials.get("PREFIXO"), case_insensitive=True)

@client.event
async def on_ready():
     print(f'Bot pronto')

chatbote = ChatBot("Ron Obvious")

trainer = ChatterBotCorpusTrainer(chatbote)
trainer.train("chatterbot.corpus.Portuguese")


@client.command()
async def chatbot(ctx, *, texto):
    async with ctx.channel.typing():
      pergunta = str(texto)
      print(pergunta)
      resposta = chatbote.get_response(pergunta)
      if float(resposta.confidence) > 0.5:
          await ctx.channel.send(resposta)
      else:
          await ctx.channel.send('Ainda não sei responder isso .\n O que eu deveria responder? Digite `,chatbot <texto>` novamente para me ensinar.')

#
client.run(credentials.get("TOKEN"))

3
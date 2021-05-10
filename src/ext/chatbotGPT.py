#import openai
import discord
import os
import gpt_2_simple as gpt2
from google_trans_new import google_translator
import tensorflow
from discord.ext import commands

translator = google_translator()
model_name = "355M"


if not os.path.isdir(os.path.join("models", model_name)):
	print(f"Downloading {model_name} model...")
	gpt2.download_gpt2(model_name=model_name)

sess = gpt2.start_tf_sess()
gpt2.load_gpt2(sess, model_name=model_name)

class GPTcog(commands.Cog, name="Chatbot"):
  def __init__(self, client: commands.Bot):
    self.client = client
#    self.start_sequence = "\nNerw:"
#    self.restart_sequence = "\n\nMembro do Gamera:"
#    self.session_prompt = ""
#    self.chlog = None
  @commands.command()
  async def nerw(self, ctx,*, question):
    ques = question
    ques = translator.translate(ques, lang_tgt='en')
    inp = 'Sofia: I am a cute 14-year teenager girl named Sofia, i loves games and dogs. My favorite artist is Pablo Vittar and my dream is to have a boyfriend.\nJoão: ' + ques + '\n' + 'Sofia:'
    print(inp)
    text = gpt2.generate(sess,
                         model_name=model_name,
                         prefix=inp,
                         length=100,
                         truncate='\n',
                         include_prefix=False,
                         temperature=0.7,
                         return_as_list=True)[0]
    text = translator.translate(text, lang_tgt='pt')
    await ctx.reply(text)
#
#    if chat_log is None: chat_log = self.session_prompt
#    if len(chat_log) >= 6100:
#      chat_log = chat_log.split("\n")
#      chat_log = f'{chat_log[len(chat_log) - 2]}\n{chat_log[len(chat_log) - 1]}'
#      print("DFALKeafnawlnawffjkasefAELFefefw")
#      print(chat_log)
#    prompt_text = f'{chat_log} {self.restart_sequence} {question} {self.start_sequence}'
#    print(f'||||| Prompt: {prompt_text} ||||||')
#    openai.api_key =
#    completion = openai.Completion.create(
#      engine="davinci",
#      n=1,
#      max_tokens=500,
#      stop=["\n"],
#      prompt=prompt_text,
#      temperature=0.7,
#      top_p=1,
#      presence_penalty=0.3,
#      frequency_penalty=0,
#      echo=True,
#    )
#    choice = completion.choices[0].text
#    choice = choice.split(":")
#    choice = choice[len(choice)-1].strip()
#    print(f'ISSO AQUI É O CHOICE Ó {choice} !!!!!!!!!!!!!!!!!!!!!')
#    return str(choice)
#
#  def append_interaction_to_chat_log(self, question, answer, chat_log=None):
#    if chat_log is None: chat_log = self.session_prompt
#    return f'{chat_log} {self.restart_sequence} {question} {self.start_sequence} {answer}'
#
#  def getres(self, log):
#    chat_log = log
#    msg = input('msg: ')
#    answer = self.ask(msg, chat_log)
#    chlog = self.append_interaction_to_chat_log(msg, answer, chat_log)
#    print(answer)
#
#  @commands.command()
#  async def nerw(self, ctx, *, question):
#    chat_log = self.chlog
#    print(chat_log)
#    answer = self.ask(question, chat_log)
#    self.chlog = self.append_interaction_to_chat_log(question, answer, chat_log)
#    try:
#      await ctx.reply(answer)
#    except discord.errors.HTTPException:
#      await ctx.reply(".....................hm")
#
#  @commands.command()
#  @commands.is_owner()
#  async def log(self, ctx):
#    with open("gameralog.txt",'w', encoding='utf-8') as file:
#      async for message in ctx.history(limit=None):
#        file.write(message.content + "\n")
#    await ctx.send("pronto mano")
#
def setup(client):
  client.add_cog(GPTcog(client))


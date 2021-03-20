from discord.ext import commands

class AllSee(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    ForbiddenVocabulary=list()
    ForbiddenArchives=list()
    Result=list("message","attention","mute","warn","kick","tempBan","permaBan")
    @commands
    async def proibitedWords(self, ctx, var:str, word:str, result:str):
           if var == "add":
              ForbiddenVocabulary.insert(len(ForbiddenVocabulary), word)
           else if var == "remove":
              ForbiddenVocabulary.remove(word)
              
              
    async def proibitedFormats(self, ctx, var:str, *,formats:str):
           if var == "add":
              ForbiddenVocabulary.insert(len(ForbiddenVocabulary),"."+formats)
           else if var == "remove":
              ForbiddenVocabulary.remove(formats)    
            
    async def on_message(self, message):
        
        if message.author == self.user:
            return

        msg = message.content
        if len(messageContent) > 0:
            for word in ForbiddenVocabulary:
                if word in messageContent:
                    await message.channel.send('Cuidado com as suas palavras!')
            
        messageattachments = message.attachments
        if len(messageattachments) > 0:
            for attachment in messageattachments:
              for formatsAll in ForbiddenArchives:
                if attachment.filename.endswith(formatsAll):
                    await message.delete()
                    await message.channel.send("Sem " + FormatsAll+" aqui!")
                else
                    pass
